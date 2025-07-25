"""
Basic Integration Test for Forecasting Models
Tests core functionality without requiring all ML dependencies

This simplified test verifies:
1. Module structure and imports
2. Basic class definitions
3. Configuration loading
4. Tool integration basics

Author: Kilo Code
Version: 1.0.0
"""

import os
import sys
import json
from datetime import datetime, timedelta

# Add the ai_assistant directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_module_structure():
    """Test that all required modules exist and have basic structure"""
    print("🔍 Testing Module Structure")
    print("-" * 30)
    
    required_files = [
        "forecasting_models.py",
        "lstm_predictor.py", 
        "stock_prediction_models.py",
        "model_training.py",
        "tools.py",
        "FORECASTING_MODELS.md"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files exist")
        return True

def test_basic_imports():
    """Test basic imports without ML dependencies"""
    print("\n🔍 Testing Basic Imports")
    print("-" * 30)
    
    try:
        # Test basic Python imports
        from datetime import datetime, timedelta
        from enum import Enum
        from dataclasses import dataclass
        from typing import Optional, List, Dict, Any, Union
        from abc import ABC, abstractmethod
        print("✅ Basic Python imports successful")
        
        # Test if we can import the module structure (not the ML parts)
        import forecasting_models
        print("✅ forecasting_models module imported")
        
        import tools
        print("✅ tools module imported")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_configuration_files():
    """Test configuration files exist and are valid JSON"""
    print("\n🔍 Testing Configuration Files")
    print("-" * 30)
    
    config_files = [
        "models/model_registry.json",
        "models/training_configs/lstm_config.json",
        "models/training_configs/xgboost_config.json",
        "models/training_configs/random_forest_config.json"
    ]
    
    all_valid = True
    
    for config_file in config_files:
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                print(f"✅ {config_file} - Valid JSON")
            except json.JSONDecodeError as e:
                print(f"❌ {config_file} - Invalid JSON: {e}")
                all_valid = False
        else:
            print(f"⚠️ {config_file} - File not found")
    
    return all_valid

def test_directory_structure():
    """Test that required directories exist"""
    print("\n🔍 Testing Directory Structure")
    print("-" * 30)
    
    required_dirs = [
        "models",
        "models/training_configs"
    ]
    
    all_exist = True
    for directory in required_dirs:
        if os.path.exists(directory) and os.path.isdir(directory):
            print(f"✅ {directory}/ - Directory exists")
        else:
            print(f"❌ {directory}/ - Directory missing")
            all_exist = False
    
    return all_exist

def test_tools_integration():
    """Test tools integration without ML dependencies"""
    print("\n🔍 Testing Tools Integration")
    print("-" * 30)
    
    try:
        # Check if tools.py has the required exports
        with open("tools.py", 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_elements = [
            "predict_stock_price_tool",
            "StockPredictionInput", 
            "parse_stock_prediction_request",
            "format_prediction_results"
        ]
        
        all_found = True
        for element in required_elements:
            if element in content:
                print(f"✅ {element} - Found in tools.py")
            else:
                print(f"❌ {element} - Not found in tools.py")
                all_found = False
        
        return all_found
        
    except Exception as e:
        print(f"❌ Error reading tools.py: {e}")
        return False

def test_documentation():
    """Test documentation exists and has required sections"""
    print("\n🔍 Testing Documentation")
    print("-" * 30)
    
    try:
        with open("FORECASTING_MODELS.md", 'r') as f:
            content = f.read()
        
        required_sections = [
            "# Forecasting Models",
            "## Architecture",
            "## Supported Models",
            "## Usage Examples",
            "## Model Training"
        ]
        
        all_found = True
        for section in required_sections:
            if section in content:
                print(f"✅ {section} - Found in documentation")
            else:
                print(f"❌ {section} - Not found in documentation")
                all_found = False
        
        return all_found
        
    except Exception as e:
        print(f"❌ Error reading documentation: {e}")
        return False

def test_query_parsing_logic():
    """Test query parsing logic without ML dependencies"""
    print("\n🔍 Testing Query Parsing Logic")
    print("-" * 30)
    
    try:
        # Test basic string parsing logic
        test_queries = [
            "Predict AAPL price for next 7 days",
            "What will GOOGL be in 30 days?",
            "Forecast MSFT using LSTM for 1 week"
        ]
        
        # Basic regex patterns that should work
        import re
        
        ticker_pattern = r'\b[A-Z]{1,5}\b'
        number_pattern = r'\b\d+\b'
        
        for query in test_queries:
            tickers = re.findall(ticker_pattern, query)
            numbers = re.findall(number_pattern, query)
            
            if tickers and numbers:
                print(f"✅ '{query}' - Parsed ticker: {tickers[0]}, number: {numbers[0]}")
            else:
                print(f"⚠️ '{query}' - Could not parse completely")
        
        return True
        
    except Exception as e:
        print(f"❌ Query parsing test failed: {e}")
        return False

def run_basic_integration_test():
    """Run all basic integration tests"""
    print("🚀 Basic Forecasting Integration Test")
    print("=" * 50)
    
    tests = [
        ("Module Structure", test_module_structure),
        ("Basic Imports", test_basic_imports),
        ("Configuration Files", test_configuration_files),
        ("Directory Structure", test_directory_structure),
        ("Tools Integration", test_tools_integration),
        ("Documentation", test_documentation),
        ("Query Parsing Logic", test_query_parsing_logic)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")
    
    if passed == total:
        print("\n🎉 All basic integration tests passed!")
        print("The forecasting system structure is correctly set up.")
        print("\nNext steps:")
        print("1. Install ML dependencies (scikit-learn, xgboost, etc.)")
        print("2. Run full integration tests")
        print("3. Test with real data")
        return True
    else:
        print(f"\n⚠️ {total - passed} tests failed.")
        print("Please fix the issues above before proceeding.")
        return False

if __name__ == "__main__":
    success = run_basic_integration_test()
    exit(0 if success else 1)