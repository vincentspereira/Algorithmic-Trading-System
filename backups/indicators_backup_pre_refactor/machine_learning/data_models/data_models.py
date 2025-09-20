from enum import Enum, auto
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

class LearningMode(Enum):
    """
    The learning mode for the adaptive system.
    """
    SUPERVISED = auto()
    REINFORCEMENT = auto()
    ENSEMBLE = auto()

class OptimizationMethod(Enum):
    """
    The optimization method for parameter tuning.
    """
    GRID_SEARCH = auto()
    RANDOM_SEARCH = auto()
    BAYESIAN = auto()

class PerformanceMetric(Enum):
    """
    The performance metric to optimize for.
    """
    SHARPE_RATIO = auto()
    SORTINO_RATIO = auto()
    PROFIT_FACTOR = auto()
    WIN_RATE = auto()

@dataclass
class PerformanceRecord:
    """
    A record of performance for a given strategy and set of parameters.
    """
    strategy_id: str
    parameters: Dict[str, Any]
    metrics: Dict[str, float]
    timestamp: str
    market_regime: Optional[str] = None
    confidence_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the record to a dictionary.
        """
        return {
            "strategy_id": self.strategy_id,
            "parameters": self.parameters,
            "metrics": self.metrics,
            "timestamp": self.timestamp,
            "market_regime": self.market_regime,
            "confidence_score": self.confidence_score,
        }

@dataclass
class LearningConfig:
    """
    Configuration for the adaptive learning system.
    """
    learning_mode: LearningMode = LearningMode.ENSEMBLE
    optimization_method: OptimizationMethod = OptimizationMethod.BAYESIAN
    primary_metric: PerformanceMetric = PerformanceMetric.SHARPE_RATIO
    performance_threshold: float = 0.5  # Minimum performance to trigger adaptation
    adaptation_interval: int = 100  # Records between adaptations
    max_parameter_change: float = 0.2  # Max % change for a parameter
    parameter_bounds: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    max_models: int = 10  # Maximum number of models to store