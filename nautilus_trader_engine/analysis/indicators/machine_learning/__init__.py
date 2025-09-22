"""
Machine Learning Analysis Suite for NautilusTrader Engine

This comprehensive suite provides institutional-grade machine learning analysis tools including:
- ML Prediction Engine: Ensemble ML models for price prediction and signal generation
- Deep Learning Analyzer: Neural networks for advanced pattern recognition and forecasting
- Adaptive Learning System: Dynamic model adaptation based on market conditions
- Neural Network Optimizer: Automated neural network architecture optimization
- Feature Engineering: Automated feature extraction from market data
- Model Validation: Rigorous backtesting and performance evaluation

All implementations include volume-weighting, smart money confirmation,
multi-timeframe analysis, adaptive confidence scoring, and integrated risk management.
"""

from .data_models import (
    LearningMode,
    OptimizationMethod,
    PerformanceMetric,
    PerformanceRecord,
    LearningConfig,
)
from .neural_network_optimizer import NeuralNetworkOptimizer
from .adaptive_learning_system import AdaptiveLearningSystem
from .factory import create_adaptive_learning_system
from .ml_prediction_engine import (
    MLPredictionEngine, MLSignal, PredictionModelType, PredictionHorizon,
    MarketRegime, ModelPerformance, MLFeatureEngineer, MarketRegimeDetector
)
from .deep_learning_analyzer import (
    DeepLearningAnalyzer, DeepLearningSignal, DeepLearningModelType,
    NeuralNetworkArchitecture, ModelTrainingMetrics
)
from .reinforcement_learning_trader import (
    ReinforcementLearningTrader, RLSignal, RLAction, RLAlgorithm,
    MarketState, Experience, RLTrainingMetrics
)

__all__ = [
    # Existing ML components
    "LearningMode",
    "OptimizationMethod",
    "PerformanceMetric",
    "PerformanceRecord",
    "LearningConfig",
    "NeuralNetworkOptimizer",
    "AdaptiveLearningSystem",
    "create_adaptive_learning_system",

    # ML Prediction Engine
    "MLPredictionEngine", "MLSignal", "PredictionModelType", "PredictionHorizon",
    "MarketRegime", "ModelPerformance", "MLFeatureEngineer", "MarketRegimeDetector",

    # Deep Learning Analyzer
    "DeepLearningAnalyzer", "DeepLearningSignal", "DeepLearningModelType",
    "NeuralNetworkArchitecture", "ModelTrainingMetrics",

    # Reinforcement Learning Trader
    "ReinforcementLearningTrader", "RLSignal", "RLAction", "RLAlgorithm",
    "MarketState", "Experience", "RLTrainingMetrics"
]