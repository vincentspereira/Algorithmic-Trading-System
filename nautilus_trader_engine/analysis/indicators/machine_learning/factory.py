from .adaptive_learning_system import AdaptiveLearningSystem
from .data_models import LearningConfig, LearningMode, OptimizationMethod, PerformanceMetric

def create_adaptive_learning_system(
    learning_mode: LearningMode = LearningMode.ENSEMBLE,
    optimization_method: OptimizationMethod = OptimizationMethod.BAYESIAN,
    primary_metric: PerformanceMetric = PerformanceMetric.SHARPE_RATIO,
    model_save_path: str = "./models/adaptive_learning",
) -> AdaptiveLearningSystem:
    """Create an adaptive learning system with a specified configuration."""
    config = LearningConfig(
        learning_mode=learning_mode,
        optimization_method=optimization_method,
        primary_metric=primary_metric,
    )
    return AdaptiveLearningSystem(config=config, model_save_path=model_save_path)