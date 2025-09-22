from .data_models import MLConfig
from .ml_enhanced_indicator_system import MLEnhancedIndicatorSystem


def create_ml_enhanced_system(config: MLConfig) -> MLEnhancedIndicatorSystem:
    """Factory function to create an instance of the ML-enhanced system."""
    return MLEnhancedIndicatorSystem(config)