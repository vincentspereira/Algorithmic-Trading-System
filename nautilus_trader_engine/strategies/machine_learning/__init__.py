#!/usr/bin/env python3
"""
Machine Learning Strategies Module

Advanced machine learning-based trading strategies leveraging supervised learning,
unsupervised learning, and reinforcement learning techniques for market prediction
and adaptive trading behavior.

This module provides:
- Supervised Learning Strategies (Random Forest, XGBoost, Neural Networks)
- Unsupervised Learning Strategies (Clustering, Anomaly Detection)
- Reinforcement Learning Strategies (Q-Learning, Policy Gradient)
- Feature Engineering and Selection
- Model Training and Validation
- Real-time Prediction and Signal Generation
- Performance Monitoring and Model Retraining

Key Components:
- feature_engineering.py: Advanced feature extraction and engineering
- supervised_strategies.py: Classification and regression-based strategies
- clustering_strategies.py: Market regime detection and clustering
- reinforcement_strategies.py: RL-based adaptive trading agents
- model_management.py: Model lifecycle management and versioning
- prediction_engine.py: Real-time prediction and inference
- performance_monitoring.py: Model performance tracking and alerts

Architecture:
Follows the 5-Pillar Architecture with machine learning enhancements:
1. Signal Generation: ML model predictions and confidence scores
2. Risk Management: Model uncertainty and prediction confidence
3. Market Regime: ML-based regime detection and adaptation
4. Execution: ML-optimized order placement and timing
5. Performance: Model performance tracking and retraining triggers
"""

# Core ML components
from .feature_engineering import (
    FeatureEngineer, FeatureConfig, TechnicalFeatures,
    PriceActionFeatures, VolumeFeatures, VolatilityFeatures,
    MarketMicrostructureFeatures, MacroeconomicFeatures,
    SentimentFeatures, AlternativeFeatures
)

# Supervised learning strategies
from .supervised_strategies import (
    BaseMLStrategy, RandomForestStrategy, XGBoostStrategy, SVMStrategy,
    NeuralNetworkStrategy, EnsembleStrategy, ModelConfig, ModelType,
    PredictionType, PredictionResult, ModelPerformance, ModelStatus,
    SignalType
)

# Model management
from .model_manager import (
    AdvancedModelManager, ModelRegistry, ModelMonitor, ABTestManager,
    ModelVersion, ModelAlert, ABTestConfig, ABTestResult,
    ModelLifecycleStage, AlertType, AlertSeverity
)

# Clustering and unsupervised learning strategies
from .clustering_strategies import (
    ClusteringStrategy, MarketRegimeDetector, AnomalyDetectionStrategy,
    RegimeType, ClusteringMethod, AnomalyMethod, RegimeState,
    ClusteringConfig, TradingState as ClusteringTradingState,
    create_clustering_strategy
)

# Reinforcement learning strategies
from .reinforcement_learning import (
    RLTradingStrategy, DQNAgent, PolicyGradientAgent, TradingEnvironment,
    ActionType, RLAlgorithm, RLConfig, TradingState as RLTradingState,
    TradingAction, ReplayBuffer, create_rl_strategy
)

__all__ = [
    # Feature Engineering
    'FeatureEngineer',
    'FeatureConfig',
    'TechnicalFeatures',
    'PriceActionFeatures', 
    'VolumeFeatures',
    'VolatilityFeatures',
    'MarketMicrostructureFeatures',
    'MacroeconomicFeatures',
    'SentimentFeatures',
    'AlternativeFeatures',
    
    # Supervised ML Strategies
    'BaseMLStrategy',
    'RandomForestStrategy',
    'XGBoostStrategy',
    'SVMStrategy',
    'NeuralNetworkStrategy',
    'EnsembleStrategy',
    'ModelConfig',
    'ModelType',
    'PredictionType',
    'PredictionResult',
    'ModelPerformance',
    'ModelStatus',
    'SignalType',
    
    # Model Management
    'AdvancedModelManager',
    'ModelRegistry',
    'ModelMonitor',
    'ABTestManager',
    'ModelVersion',
    'ModelAlert',
    'ABTestConfig',
    'ABTestResult',
    'ModelLifecycleStage',
    'AlertType',
    'AlertSeverity',
    
    # Clustering and Unsupervised Learning
    'ClusteringStrategy',
    'MarketRegimeDetector',
    'AnomalyDetectionStrategy',
    'RegimeType',
    'ClusteringMethod',
    'AnomalyMethod',
    'RegimeState',
    'ClusteringConfig',
    'ClusteringTradingState',
    'create_clustering_strategy',
    
    # Reinforcement Learning
    'RLTradingStrategy',
    'DQNAgent',
    'PolicyGradientAgent',
    'TradingEnvironment',
    'ActionType',
    'RLAlgorithm',
    'RLConfig',
    'RLTradingState',
    'TradingAction',
    'ReplayBuffer',
    'create_rl_strategy'
]

# Module metadata
__version__ = '1.0.0'
__author__ = 'Algorithmic Trading System'
__description__ = 'Advanced machine learning strategies for algorithmic trading'
__license__ = 'MIT'

# Configuration
DEFAULT_CONFIG = {
    'feature_engineering': {
        'lookback_periods': [5, 10, 20, 50, 100, 200],
        'technical_indicators': True,
        'market_microstructure': True,
        'sentiment_features': False,
        'macro_features': False
    },
    'model_training': {
        'train_test_split': 0.8,
        'validation_split': 0.2,
        'cross_validation_folds': 5,
        'hyperparameter_tuning': True,
        'early_stopping': True
    },
    'prediction': {
        'confidence_threshold': 0.6,
        'ensemble_voting': 'soft',
        'prediction_horizon': 1,
        'update_frequency': 'daily'
    },
    'performance_monitoring': {
        'drift_detection': True,
        'performance_threshold': 0.55,
        'retraining_frequency': 'monthly',
        'model_validation': True
    }
}