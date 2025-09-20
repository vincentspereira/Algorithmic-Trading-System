import json
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .data_models import LearningConfig, PerformanceRecord
from .neural_network_optimizer import NeuralNetworkOptimizer

class AdaptiveLearningSystem:
    """
    An adaptive system for optimizing trading strategy parameters.
    """

    def __init__(self, config: LearningConfig, model_save_path: str = "./models/adaptive_learning"):
        self.config = config
        self.model_save_path = Path(model_save_path)
        self.model_save_path.mkdir(parents=True, exist_ok=True)

        self.performance_history: deque[PerformanceRecord] = deque(maxlen=1000)
        self.regime_performance: Dict[str, List[PerformanceRecord]] = {}
        self.current_parameters: Dict[str, Any] = self._get_default_parameters()
        self.best_performance: Optional[PerformanceRecord] = None
        self.adaptation_count = 0
        self.last_adaptation: Optional[datetime] = None

        self.models: Dict[str, Any] = {}
        self.current_model_id: Optional[str] = None

        self.executor = ThreadPoolExecutor(max_workers=2)
        self.logger = logging.getLogger(__name__)

        if torch.cuda.is_available():
            self.device = torch.device("cuda")
            self.logger.info("Using CUDA for neural network optimization")
        else:
            self.device = torch.device("cpu")
            self.logger.info("Using CPU for neural network optimization")

        # Initialize the neural network optimizer
        self.nn_optimizer: Optional[NeuralNetworkOptimizer] = None

    def add_performance_record(
        self, strategy_id: str, parameters: Dict[str, Any], returns: List[float], market_regime: Optional[str] = None
    ) -> None:
        """
        Add a new performance record to the system.
        """
        metrics = self._calculate_performance_metrics(returns)
        confidence_score = self._calculate_confidence_score(metrics)

        record = PerformanceRecord(
            strategy_id=strategy_id,
            parameters=parameters,
            metrics=metrics,
            timestamp=datetime.now(timezone.utc).isoformat(),
            market_regime=market_regime,
            confidence_score=confidence_score,
        )

        self.performance_history.append(record)

        if market_regime:
            if market_regime not in self.regime_performance:
                self.regime_performance[market_regime] = []
            self.regime_performance[market_regime].append(record)

        if self.best_performance is None or record.metrics.get(self.config.primary_metric.value, 0) > self.best_performance.metrics.get(self.config.primary_metric.value, 0):
            self.best_performance = record

        if self._should_adapt():
            self.executor.submit(self._adapt_parameters)

    def _calculate_performance_metrics(self, returns: List[float]) -> Dict[str, float]:
        """
        Calculate performance metrics from a list of returns.
        """
        if not returns:
            return {}

        returns_series = pd.Series(returns)
        total_return = (returns_series + 1).prod() - 1
        sharpe_ratio = returns_series.mean() / returns_series.std() if returns_series.std() > 0 else 0.0
        sortino_ratio = returns_series.mean() / returns_series[returns_series < 0].std() if returns_series[returns_series < 0].std() > 0 else 0.0
        win_rate = (returns_series > 0).sum() / len(returns_series) if len(returns_series) > 0 else 0.0

        return {
            "total_return": total_return,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "win_rate": win_rate,
        }

    def _calculate_confidence_score(self, metrics: Dict[str, float]) -> float:
        """
        Calculate a confidence score based on performance metrics.
        """
        primary_metric_score = metrics.get(self.config.primary_metric.value, 0.0)
        return np.clip(primary_metric_score, 0, 1)  # Simplified

    def _should_adapt(self) -> bool:
        """
        Determine if the system should adapt its parameters.
        """
        if len(self.performance_history) < self.config.adaptation_interval:
            return False

        recent_performance = self._get_recent_performance()
        if recent_performance < self.config.performance_threshold:
            return True

        return False

    def _get_recent_performance(self) -> float:
        """
        Get the average performance over the recent adaptation interval.
        """
        if not self.performance_history:
            return 0.0

        recent_records = list(self.performance_history)[-self.config.adaptation_interval:]
        return np.mean([r.metrics.get(self.config.primary_metric.value, 0) for r in recent_records])

    def _adapt_parameters(self) -> None:
        """
        Adapt the strategy parameters based on recent performance.
        """
        self.logger.info("Starting parameter adaptation...")
        self.adaptation_count += 1
        self.last_adaptation = datetime.now(timezone.utc)

        new_parameters = self.current_parameters

        if self.config.learning_mode == LearningMode.SUPERVISED:
            new_parameters = self._supervised_learning()
        elif self.config.learning_mode == LearningMode.REINFORCEMENT:
            new_parameters = self._reinforcement_learning()
        elif self.config.learning_mode == LearningMode.ENSEMBLE:
            new_parameters = self._ensemble_learning()

        if self._validate_parameters(new_parameters):
            self._update_parameters(new_parameters)
            self.logger.info(f"Parameters adapted: {new_parameters}")
        else:
            self.logger.warning("Adaptation failed: new parameters are invalid.")

    def _supervised_learning(self) -> Dict[str, Any]:
        """
        Use supervised learning to find optimal parameters.
        """
        X_train, y_train = self._prepare_training_data()

        if self.nn_optimizer is None:
            input_dim = X_train.shape[1]
            output_dim = y_train.shape[1]
            self.nn_optimizer = NeuralNetworkOptimizer(input_dim, output_dim).to(self.device)

        self.nn_optimizer.train_model(X_train, y_train)

        # Predict new parameters based on the latest features
        latest_features = self._extract_features(self.performance_history[-1])
        predicted_params = self.nn_optimizer.predict_parameters(latest_features)

        return self._generate_parameters_from_prediction(predicted_params)

    def _reinforcement_learning(self) -> Dict[str, Any]:
        """
        Use reinforcement learning to find optimal parameters (simplified).
        """
        # Placeholder for a proper RL implementation
        return self._random_search_optimization()

    def _ensemble_learning(self) -> Dict[str, Any]:
        """
        Use an ensemble of methods to find optimal parameters.
        """
        # Combine supervised and random search
        supervised_params = self._supervised_learning()
        random_params = self._random_search_optimization()

        # Simple averaging
        new_parameters = {}
        for key in supervised_params:
            new_parameters[key] = (supervised_params[key] + random_params[key]) / 2

        return new_parameters

    def _prepare_training_data(self) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Prepare training data for the neural network.
        """
        features = []
        targets = []

        for record in self.performance_history:
            features.append(self._extract_features(record))
            targets.append(list(record.parameters.values()))

        return torch.tensor(features, dtype=torch.float32).to(self.device), torch.tensor(targets, dtype=torch.float32).to(self.device)

    def _extract_features(self, record: PerformanceRecord) -> List[float]:
        """
        Extract features from a performance record.
        """
        # Example features: metrics and market regime
        features = list(record.metrics.values())
        # Add more features here, e.g., one-hot encoded market regime
        return features

    def _generate_parameters_from_prediction(self, prediction: torch.Tensor) -> Dict[str, Any]:
        """
        Generate a parameter dictionary from a model's prediction.
        """
        param_values = prediction.cpu().numpy().flatten()
        param_keys = list(self.config.parameter_bounds.keys())
        return dict(zip(param_keys, param_values))

    def _random_search_optimization(self) -> Dict[str, Any]:
        """
        Perform random search optimization.
        """
        if not self.config.parameter_bounds:
            return self._get_default_parameters()

        new_parameters = {}
        for param_name, (min_val, max_val) in self.config.parameter_bounds.items():
            new_parameters[param_name] = np.random.uniform(min_val, max_val)

        return new_parameters

    def _validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Validate the new parameters.
        """
        if not parameters:
            return False

        for param_name, param_value in parameters.items():
            if param_name in self.config.parameter_bounds:
                min_val, max_val = self.config.parameter_bounds[param_name]
                if not (min_val <= param_value <= max_val):
                    return False

        if self.current_parameters:
            for param_name, new_value in parameters.items():
                if param_name in self.current_parameters:
                    old_value = self.current_parameters[param_name]
                    if isinstance(old_value, (int, float)) and old_value != 0:
                        change_ratio = abs(new_value - old_value) / abs(old_value)
                        if change_ratio > self.config.max_parameter_change:
                            return False
        return True

    def _update_parameters(self, new_parameters: Dict[str, Any]) -> None:
        """
        Update the current parameters.
        """
        self.current_parameters = new_parameters.copy()
        self._save_model_state()

    def _get_default_parameters(self) -> Dict[str, Any]:
        """
        Get the default parameters.
        """
        defaults = {}
        for param_name, (min_val, max_val) in self.config.parameter_bounds.items():
            defaults[param_name] = (min_val + max_val) / 2
        return defaults

    def get_current_parameters(self) -> Dict[str, Any]:
        """
        Get the current optimized parameters.
        """
        return self.current_parameters.copy()

    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive performance summary.
        """
        if not self.performance_history:
            return {}

        records = list(self.performance_history)
        total_records = len(records)
        avg_confidence = np.mean([r.confidence_score for r in records])

        regime_stats = {}
        for regime, regime_records in self.regime_performance.items():
            if regime_records:
                regime_performance = [r.metrics.get(self.config.primary_metric.value, 0) for r in regime_records]
                regime_stats[regime] = {
                    'count': len(regime_records),
                    'avg_performance': np.mean(regime_performance),
                    'std_performance': np.std(regime_performance)
                }

        recent_performance = self._get_recent_performance()

        return {
            'total_records': total_records,
            'avg_confidence': avg_confidence,
            'adaptation_count': self.adaptation_count,
            'last_adaptation': self.last_adaptation.isoformat() if self.last_adaptation else None,
            'recent_performance': recent_performance,
            'best_performance': self.best_performance,
            'regime_statistics': regime_stats,
            'current_parameters': self.current_parameters
        }

    def _save_model_state(self) -> None:
        """
        Save the current model state.
        """
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            model_id = f"adaptive_model_{timestamp}"

            state = {
                'model_id': model_id,
                'timestamp': timestamp,
                'parameters': self.current_parameters,
                'performance_history': [r.to_dict() for r in list(self.performance_history)],
                'config': {
                    'learning_mode': self.config.learning_mode.value,
                    'optimization_method': self.config.optimization_method.value,
                    'primary_metric': self.config.primary_metric.value
                }
            }

            save_path = self.model_save_path / f"{model_id}.json"
            with open(save_path, 'w') as f:
                json.dump(state, f, indent=2)

            self.models[model_id] = state
            self.current_model_id = model_id

            self._cleanup_old_models()

        except Exception as e:
            self.logger.error(f"Error saving model state: {e}")

    def _cleanup_old_models(self) -> None:
        """
        Remove old model files to save space.
        """
        if len(self.models) <= self.config.max_models:
            return

        sorted_models = sorted(self.models.items(), key=lambda x: x[1]['timestamp'])
        models_to_remove = sorted_models[:-self.config.max_models]

        for model_id, _ in models_to_remove:
            try:
                model_file = self.model_save_path / f"{model_id}.json"
                if model_file.exists():
                    model_file.unlink()
                del self.models[model_id]
            except Exception as e:
                self.logger.error(f"Error removing old model {model_id}: {e}")

    def load_model_state(self, model_id: str) -> bool:
        """
        Load a specific model state.
        """
        try:
            model_file = self.model_save_path / f"{model_id}.json"
            if not model_file.exists():
                self.logger.error(f"Model file not found: {model_file}")
                return False

            with open(model_file, 'r') as f:
                state = json.load(f)

            self.current_parameters = state['parameters']
            self.current_model_id = model_id
            self.logger.info(f"Model state loaded successfully: {model_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error loading model state: {e}")
            return False

    def rollback_to_best_model(self) -> bool:
        """
        Rollback to the best performing model.
        """
        if not self.models:
            return False

        best_model_id = None
        best_score = float('-inf')

        for model_id, model_data in self.models.items():
            if 'performance_history' in model_data:
                performances = []
                for record_dict in model_data['performance_history']:
                    if 'metrics' in record_dict:
                        metric_key = self.config.primary_metric.value
                        if metric_key in record_dict['metrics']:
                            performances.append(record_dict['metrics'][metric_key])
                
                if performances:
                    avg_performance = np.mean(performances)
                    if avg_performance > best_score:
                        best_score = avg_performance
                        best_model_id = model_id
        
        if best_model_id:
            return self.load_model_state(best_model_id)
        
        return False

    def set_parameter_bounds(self, parameter_bounds: Dict[str, Tuple[float, float]]) -> None:
        """
        Set parameter bounds for optimization.
        """
        self.config.parameter_bounds = parameter_bounds.copy()

    def shutdown(self) -> None:
        """
        Shutdown the adaptive learning system.
        """
        self.executor.shutdown(wait=True)
        self.logger.info("Adaptive learning system shutdown complete")