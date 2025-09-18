"""Machine Learning Enhanced Technical Indicators

This module contains technical indicators enhanced with machine learning capabilities
for adaptive behavior, regime detection, and intelligent signal generation.

Components:
===========
- adaptive_learning_system: ML-based indicator adaptation system
- ml_enhanced_system: Machine learning enhanced indicator framework
- regime_adaptation_engine: Market regime detection and adaptation

Key Features:
=============
- Adaptive parameter optimization using ML algorithms
- Market regime detection with clustering and classification
- Dynamic indicator behavior based on market conditions
- Real-time learning and adaptation capabilities
- Integration with scikit-learn and TensorFlow

Usage:
======
from nautilus_trader_engine.indicators.machine_learning import (
    adaptive_learning_system,
    ml_enhanced_system,
    regime_adaptation_engine
)

# Initialize adaptive learning system
adaptive_system = adaptive_learning_system.AdaptiveLearningSystem()

# Detect market regime
regime_engine = regime_adaptation_engine.RegimeAdaptationEngine()
current_regime = regime_engine.detect_regime(market_data)

# Apply ML-enhanced indicators
ml_system = ml_enhanced_system.MLEnhancedSystem()
enhanced_signals = ml_system.generate_signals(price_data, regime=current_regime)
"""

try:
    from . import adaptive_learning_system
    from . import ml_enhanced_system
    from . import regime_adaptation_engine
except ImportError:
    # Handle missing dependencies gracefully
    pass

__all__ = [
    'adaptive_learning_system',
    'ml_enhanced_system',
    'regime_adaptation_engine'
]