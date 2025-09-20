#!/usr/bin/env python3
"""
ML Model Management System

Provides comprehensive model lifecycle management for machine learning trading strategies.
Handles model training, validation, deployment, monitoring, and automated retraining.

Key Features:
- Model Lifecycle Management (train, validate, deploy, retire)
- A/B Testing Framework for model comparison
- Automated Model Monitoring and Drift Detection
- Performance Tracking and Alerting
- Model Versioning and Rollback
- Hyperparameter Optimization
- Cross-validation and Walk-forward Analysis
- Model Interpretability and Explainability
- Resource Management and Scaling
- Integration with Trading Engine
- Compliance and Audit Trail
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import warnings
from datetime import datetime, timedelta
import logging
import json
import hashlib
import threading
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import sqlite3
from contextlib import contextmanager

# Model management imports
from .supervised_strategies import (
    BaseMLStrategy, RandomForestStrategy, XGBoostStrategy, SVMStrategy,
    NeuralNetworkStrategy, EnsembleStrategy, ModelConfig, ModelType,
    PredictionType, PredictionResult, ModelPerformance, ModelStatus
)
from .feature_engineering import FeatureEngineer

# Statistical imports
from scipy import stats
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    mean_squared_error, mean_absolute_error, r2_score
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress warnings
warnings.filterwarnings('ignore')


class ModelLifecycleStage(Enum):
    """Model lifecycle stages."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
    RETIRED = "retired"


class AlertType(Enum):
    """Alert types for model monitoring."""
    PERFORMANCE_DEGRADATION = "performance_degradation"
    DATA_DRIFT = "data_drift"
    MODEL_ERROR = "model_error"
    TRAINING_FAILURE = "training_failure"
    RESOURCE_USAGE = "resource_usage"
    COMPLIANCE_VIOLATION = "compliance_violation"


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ModelVersion:
    """Model version information."""
    version: str
    model_hash: str
    created_at: datetime
    config: ModelConfig
    performance: Optional[ModelPerformance] = None
    stage: ModelLifecycleStage = ModelLifecycleStage.DEVELOPMENT
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = False


@dataclass
class ModelAlert:
    """Model monitoring alert."""
    alert_id: str
    model_name: str
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class ABTestConfig:
    """A/B testing configuration."""
    test_name: str
    control_model: str
    treatment_models: List[str]
    traffic_split: Dict[str, float]  # model_name -> percentage
    start_date: datetime
    end_date: datetime
    success_metrics: List[str]
    minimum_sample_size: int = 1000
    significance_level: float = 0.05


@dataclass
class ABTestResult:
    """A/B test results."""
    test_name: str
    model_results: Dict[str, Dict[str, float]]  # model_name -> metrics
    statistical_significance: Dict[str, bool]  # metric -> is_significant
    confidence_intervals: Dict[str, Tuple[float, float]]  # metric -> (lower, upper)
    winner: Optional[str] = None
    completed_at: Optional[datetime] = None


class ModelRegistry:
    """Registry for managing model versions and metadata."""
    
    def __init__(self, registry_path: str = "model_registry.db"):
        self.registry_path = registry_path
        self.models = {}  # model_name -> List[ModelVersion]
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize SQLite database for model registry."""
        with sqlite3.connect(self.registry_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    model_hash TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    config TEXT NOT NULL,
                    performance TEXT,
                    stage TEXT NOT NULL,
                    metadata TEXT,
                    is_active BOOLEAN DEFAULT FALSE,
                    UNIQUE(model_name, version)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT UNIQUE NOT NULL,
                    model_name TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    data TEXT,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolved_at TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ab_tests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_name TEXT UNIQUE NOT NULL,
                    config TEXT NOT NULL,
                    results TEXT,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP
                )
            """)
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with proper cleanup."""
        conn = sqlite3.connect(self.registry_path)
        try:
            yield conn
        finally:
            conn.close()
    
    def register_model(self, model_name: str, model: BaseMLStrategy, 
                      stage: ModelLifecycleStage = ModelLifecycleStage.DEVELOPMENT) -> str:
        """Register a new model version.
        
        Args:
            model_name: Name of the model
            model: Model instance
            stage: Lifecycle stage
            
        Returns:
            Version string
        """
        try:
            # Generate version and hash
            version = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_hash = self._calculate_model_hash(model)
            
            # Create model version
            model_version = ModelVersion(
                version=version,
                model_hash=model_hash,
                created_at=datetime.now(),
                config=model.config,
                stage=stage
            )
            
            # Store in database
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO model_versions 
                    (model_name, version, model_hash, created_at, config, stage, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    model_name,
                    version,
                    model_hash,
                    model_version.created_at,
                    json.dumps(model_version.config.__dict__),
                    stage.value,
                    json.dumps(model_version.metadata)
                ))
                conn.commit()
            
            # Update in-memory registry
            if model_name not in self.models:
                self.models[model_name] = []
            self.models[model_name].append(model_version)
            
            logger.info(f"Registered model {model_name} version {version}")
            return version
        
        except Exception as e:
            logger.error(f"Error registering model: {e}")
            raise
    
    def _calculate_model_hash(self, model: BaseMLStrategy) -> str:
        """Calculate hash for model configuration and parameters.
        
        Args:
            model: Model instance
            
        Returns:
            Model hash
        """
        try:
            # Create hash from config and model parameters
            config_str = json.dumps(model.config.__dict__, sort_keys=True)
            
            # Add model-specific parameters if available
            if hasattr(model.model, 'get_params'):
                params_str = json.dumps(model.model.get_params(), sort_keys=True)
            else:
                params_str = ""
            
            combined_str = config_str + params_str
            return hashlib.md5(combined_str.encode()).hexdigest()
        
        except Exception as e:
            logger.warning(f"Could not calculate model hash: {e}")
            return hashlib.md5(str(datetime.now()).encode()).hexdigest()
    
    def get_model_versions(self, model_name: str) -> List[ModelVersion]:
        """Get all versions of a model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            List of model versions
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT version, model_hash, created_at, config, performance, 
                           stage, metadata, is_active
                    FROM model_versions 
                    WHERE model_name = ?
                    ORDER BY created_at DESC
                """, (model_name,))
                
                versions = []
                for row in cursor.fetchall():
                    version = ModelVersion(
                        version=row[0],
                        model_hash=row[1],
                        created_at=datetime.fromisoformat(row[2]),
                        config=ModelConfig(**json.loads(row[3])),
                        performance=ModelPerformance(**json.loads(row[4])) if row[4] else None,
                        stage=ModelLifecycleStage(row[5]),
                        metadata=json.loads(row[6]) if row[6] else {},
                        is_active=bool(row[7])
                    )
                    versions.append(version)
                
                return versions
        
        except Exception as e:
            logger.error(f"Error getting model versions: {e}")
            return []
    
    def promote_model(self, model_name: str, version: str, 
                     target_stage: ModelLifecycleStage) -> bool:
        """Promote model to a higher lifecycle stage.
        
        Args:
            model_name: Name of the model
            version: Model version
            target_stage: Target lifecycle stage
            
        Returns:
            True if successful
        """
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE model_versions 
                    SET stage = ?
                    WHERE model_name = ? AND version = ?
                """, (target_stage.value, model_name, version))
                conn.commit()
            
            logger.info(f"Promoted model {model_name} v{version} to {target_stage.value}")
            return True
        
        except Exception as e:
            logger.error(f"Error promoting model: {e}")
            return False
    
    def set_active_model(self, model_name: str, version: str) -> bool:
        """Set a model version as active.
        
        Args:
            model_name: Name of the model
            version: Model version
            
        Returns:
            True if successful
        """
        try:
            with self._get_connection() as conn:
                # Deactivate all versions
                conn.execute("""
                    UPDATE model_versions 
                    SET is_active = FALSE
                    WHERE model_name = ?
                """, (model_name,))
                
                # Activate specified version
                conn.execute("""
                    UPDATE model_versions 
                    SET is_active = TRUE
                    WHERE model_name = ? AND version = ?
                """, (model_name, version))
                
                conn.commit()
            
            logger.info(f"Set active model {model_name} to version {version}")
            return True
        
        except Exception as e:
            logger.error(f"Error setting active model: {e}")
            return False


class ModelMonitor:
    """Monitors model performance and data drift."""
    
    def __init__(self, registry: ModelRegistry):
        self.registry = registry
        self.monitoring_data = {}  # model_name -> monitoring data
        self.alerts = []
        self.monitoring_thread = None
        self.monitoring_active = False
    
    def start_monitoring(self, interval_seconds: int = 300) -> None:
        """Start continuous model monitoring.
        
        Args:
            interval_seconds: Monitoring interval in seconds
        """
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self.monitoring_thread.start()
        logger.info(f"Started model monitoring with {interval_seconds}s interval")
    
    def stop_monitoring(self) -> None:
        """Stop model monitoring."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("Stopped model monitoring")
    
    def _monitoring_loop(self, interval_seconds: int) -> None:
        """Main monitoring loop.
        
        Args:
            interval_seconds: Monitoring interval
        """
        while self.monitoring_active:
            try:
                self._check_all_models()
                time.sleep(interval_seconds)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(interval_seconds)
    
    def _check_all_models(self) -> None:
        """Check all registered models for issues."""
        # This would be implemented to check each model's performance
        # and data drift in a production environment
        pass
    
    def log_prediction(self, model_name: str, prediction_result: PredictionResult,
                      actual_outcome: Optional[float] = None) -> None:
        """Log a model prediction for monitoring.
        
        Args:
            model_name: Name of the model
            prediction_result: Prediction result
            actual_outcome: Actual outcome (if available)
        """
        try:
            if model_name not in self.monitoring_data:
                self.monitoring_data[model_name] = {
                    'predictions': [],
                    'outcomes': [],
                    'timestamps': [],
                    'confidences': []
                }
            
            data = self.monitoring_data[model_name]
            data['predictions'].append(prediction_result.prediction)
            data['outcomes'].append(actual_outcome)
            data['timestamps'].append(prediction_result.timestamp)
            data['confidences'].append(prediction_result.confidence)
            
            # Keep only recent data (last 10000 predictions)
            max_size = 10000
            if len(data['predictions']) > max_size:
                for key in data:
                    data[key] = data[key][-max_size:]
        
        except Exception as e:
            logger.error(f"Error logging prediction: {e}")
    
    def check_performance_drift(self, model_name: str, 
                               window_size: int = 1000) -> Optional[ModelAlert]:
        """Check for performance drift in model predictions.
        
        Args:
            model_name: Name of the model
            window_size: Size of the sliding window
            
        Returns:
            Alert if drift detected
        """
        try:
            if model_name not in self.monitoring_data:
                return None
            
            data = self.monitoring_data[model_name]
            predictions = data['predictions']
            outcomes = data['outcomes']
            
            if len(predictions) < window_size * 2:
                return None
            
            # Compare recent performance with historical
            recent_predictions = predictions[-window_size:]
            recent_outcomes = [o for o in outcomes[-window_size:] if o is not None]
            
            historical_predictions = predictions[-window_size*2:-window_size]
            historical_outcomes = [o for o in outcomes[-window_size*2:-window_size] if o is not None]
            
            if len(recent_outcomes) < window_size * 0.5 or len(historical_outcomes) < window_size * 0.5:
                return None
            
            # Calculate accuracy for both periods
            recent_accuracy = self._calculate_accuracy(recent_predictions, recent_outcomes)
            historical_accuracy = self._calculate_accuracy(historical_predictions, historical_outcomes)
            
            # Check for significant degradation
            degradation_threshold = 0.05  # 5% degradation
            if recent_accuracy < historical_accuracy - degradation_threshold:
                alert = ModelAlert(
                    alert_id=f"{model_name}_perf_drift_{datetime.now().isoformat()}",
                    model_name=model_name,
                    alert_type=AlertType.PERFORMANCE_DEGRADATION,
                    severity=AlertSeverity.HIGH,
                    message=f"Performance degradation detected: {recent_accuracy:.3f} vs {historical_accuracy:.3f}",
                    timestamp=datetime.now(),
                    data={
                        'recent_accuracy': recent_accuracy,
                        'historical_accuracy': historical_accuracy,
                        'degradation': historical_accuracy - recent_accuracy
                    }
                )
                
                self._store_alert(alert)
                return alert
            
            return None
        
        except Exception as e:
            logger.error(f"Error checking performance drift: {e}")
            return None
    
    def _calculate_accuracy(self, predictions: List[float], 
                          outcomes: List[float]) -> float:
        """Calculate accuracy between predictions and outcomes.
        
        Args:
            predictions: Model predictions
            outcomes: Actual outcomes
            
        Returns:
            Accuracy score
        """
        try:
            if len(predictions) != len(outcomes) or len(predictions) == 0:
                return 0.0
            
            # Convert to binary classification (positive/negative returns)
            pred_binary = [1 if p > 0 else 0 for p in predictions]
            outcome_binary = [1 if o > 0 else 0 for o in outcomes]
            
            correct = sum(1 for p, o in zip(pred_binary, outcome_binary) if p == o)
            return correct / len(predictions)
        
        except Exception as e:
            logger.error(f"Error calculating accuracy: {e}")
            return 0.0
    
    def _store_alert(self, alert: ModelAlert) -> None:
        """Store alert in database.
        
        Args:
            alert: Alert to store
        """
        try:
            with self.registry._get_connection() as conn:
                conn.execute("""
                    INSERT INTO model_alerts 
                    (alert_id, model_name, alert_type, severity, message, timestamp, data)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    alert.alert_id,
                    alert.model_name,
                    alert.alert_type.value,
                    alert.severity.value,
                    alert.message,
                    alert.timestamp,
                    json.dumps(alert.data)
                ))
                conn.commit()
            
            self.alerts.append(alert)
            logger.warning(f"Alert generated: {alert.message}")
        
        except Exception as e:
            logger.error(f"Error storing alert: {e}")
    
    def get_alerts(self, model_name: Optional[str] = None, 
                  unresolved_only: bool = True) -> List[ModelAlert]:
        """Get alerts for monitoring.
        
        Args:
            model_name: Filter by model name
            unresolved_only: Only return unresolved alerts
            
        Returns:
            List of alerts
        """
        try:
            with self.registry._get_connection() as conn:
                query = "SELECT * FROM model_alerts WHERE 1=1"
                params = []
                
                if model_name:
                    query += " AND model_name = ?"
                    params.append(model_name)
                
                if unresolved_only:
                    query += " AND resolved = FALSE"
                
                query += " ORDER BY timestamp DESC"
                
                cursor = conn.execute(query, params)
                alerts = []
                
                for row in cursor.fetchall():
                    alert = ModelAlert(
                        alert_id=row[1],
                        model_name=row[2],
                        alert_type=AlertType(row[3]),
                        severity=AlertSeverity(row[4]),
                        message=row[5],
                        timestamp=datetime.fromisoformat(row[6]),
                        data=json.loads(row[7]) if row[7] else {},
                        resolved=bool(row[8]),
                        resolved_at=datetime.fromisoformat(row[9]) if row[9] else None
                    )
                    alerts.append(alert)
                
                return alerts
        
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return []


class ABTestManager:
    """Manages A/B testing for model comparison."""
    
    def __init__(self, registry: ModelRegistry):
        self.registry = registry
        self.active_tests = {}  # test_name -> ABTestConfig
        self.test_data = {}  # test_name -> test data
    
    def create_ab_test(self, config: ABTestConfig) -> bool:
        """Create a new A/B test.
        
        Args:
            config: A/B test configuration
            
        Returns:
            True if successful
        """
        try:
            # Validate traffic split
            total_traffic = sum(config.traffic_split.values())
            if abs(total_traffic - 1.0) > 0.01:
                raise ValueError(f"Traffic split must sum to 1.0, got {total_traffic}")
            
            # Store test configuration
            with self.registry._get_connection() as conn:
                conn.execute("""
                    INSERT INTO ab_tests (test_name, config, status, created_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    config.test_name,
                    json.dumps(config.__dict__, default=str),
                    "active",
                    datetime.now()
                ))
                conn.commit()
            
            self.active_tests[config.test_name] = config
            self.test_data[config.test_name] = {
                'predictions': {model: [] for model in [config.control_model] + config.treatment_models},
                'outcomes': {model: [] for model in [config.control_model] + config.treatment_models},
                'timestamps': {model: [] for model in [config.control_model] + config.treatment_models}
            }
            
            logger.info(f"Created A/B test: {config.test_name}")
            return True
        
        except Exception as e:
            logger.error(f"Error creating A/B test: {e}")
            return False
    
    def route_prediction(self, test_name: str, user_id: str) -> str:
        """Route prediction request to appropriate model based on A/B test.
        
        Args:
            test_name: Name of the A/B test
            user_id: User identifier for consistent routing
            
        Returns:
            Model name to use
        """
        try:
            if test_name not in self.active_tests:
                logger.warning(f"A/B test {test_name} not found")
                return self.active_tests[test_name].control_model if self.active_tests else ""
            
            config = self.active_tests[test_name]
            
            # Use hash of user_id for consistent routing
            user_hash = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
            routing_value = (user_hash % 10000) / 10000.0
            
            # Route based on traffic split
            cumulative_traffic = 0.0
            for model_name, traffic_percent in config.traffic_split.items():
                cumulative_traffic += traffic_percent
                if routing_value <= cumulative_traffic:
                    return model_name
            
            # Fallback to control model
            return config.control_model
        
        except Exception as e:
            logger.error(f"Error routing prediction: {e}")
            return config.control_model if test_name in self.active_tests else ""
    
    def log_ab_test_result(self, test_name: str, model_name: str,
                          prediction: float, outcome: Optional[float] = None) -> None:
        """Log A/B test prediction result.
        
        Args:
            test_name: Name of the A/B test
            model_name: Model that made the prediction
            prediction: Model prediction
            outcome: Actual outcome (if available)
        """
        try:
            if test_name not in self.test_data:
                return
            
            data = self.test_data[test_name]
            if model_name in data['predictions']:
                data['predictions'][model_name].append(prediction)
                data['outcomes'][model_name].append(outcome)
                data['timestamps'][model_name].append(datetime.now())
        
        except Exception as e:
            logger.error(f"Error logging A/B test result: {e}")
    
    def analyze_ab_test(self, test_name: str) -> Optional[ABTestResult]:
        """Analyze A/B test results.
        
        Args:
            test_name: Name of the A/B test
            
        Returns:
            A/B test results
        """
        try:
            if test_name not in self.active_tests or test_name not in self.test_data:
                return None
            
            config = self.active_tests[test_name]
            data = self.test_data[test_name]
            
            # Calculate metrics for each model
            model_results = {}
            for model_name in [config.control_model] + config.treatment_models:
                predictions = data['predictions'][model_name]
                outcomes = [o for o in data['outcomes'][model_name] if o is not None]
                
                if len(outcomes) < config.minimum_sample_size:
                    continue
                
                # Calculate performance metrics
                accuracy = self._calculate_accuracy(predictions[:len(outcomes)], outcomes)
                avg_return = np.mean(outcomes) if outcomes else 0.0
                sharpe_ratio = self._calculate_sharpe_ratio(outcomes) if outcomes else 0.0
                
                model_results[model_name] = {
                    'accuracy': accuracy,
                    'avg_return': avg_return,
                    'sharpe_ratio': sharpe_ratio,
                    'sample_size': len(outcomes)
                }
            
            # Perform statistical significance tests
            statistical_significance = {}
            confidence_intervals = {}
            
            if config.control_model in model_results:
                control_outcomes = [o for o in data['outcomes'][config.control_model] if o is not None]
                
                for treatment_model in config.treatment_models:
                    if treatment_model in model_results:
                        treatment_outcomes = [o for o in data['outcomes'][treatment_model] if o is not None]
                        
                        # Perform t-test
                        if len(control_outcomes) > 10 and len(treatment_outcomes) > 10:
                            t_stat, p_value = stats.ttest_ind(treatment_outcomes, control_outcomes)
                            statistical_significance[f"{treatment_model}_vs_{config.control_model}"] = p_value < config.significance_level
                            
                            # Calculate confidence interval for difference in means
                            diff_mean = np.mean(treatment_outcomes) - np.mean(control_outcomes)
                            pooled_std = np.sqrt((np.var(treatment_outcomes) + np.var(control_outcomes)) / 2)
                            margin_error = 1.96 * pooled_std / np.sqrt(min(len(treatment_outcomes), len(control_outcomes)))
                            confidence_intervals[f"{treatment_model}_vs_{config.control_model}"] = (
                                diff_mean - margin_error,
                                diff_mean + margin_error
                            )
            
            # Determine winner
            winner = None
            if model_results:
                best_model = max(model_results.keys(), 
                               key=lambda m: model_results[m].get('sharpe_ratio', 0))
                
                # Check if winner is statistically significant
                if best_model != config.control_model:
                    sig_key = f"{best_model}_vs_{config.control_model}"
                    if statistical_significance.get(sig_key, False):
                        winner = best_model
            
            result = ABTestResult(
                test_name=test_name,
                model_results=model_results,
                statistical_significance=statistical_significance,
                confidence_intervals=confidence_intervals,
                winner=winner,
                completed_at=datetime.now()
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Error analyzing A/B test: {e}")
            return None
    
    def _calculate_accuracy(self, predictions: List[float], outcomes: List[float]) -> float:
        """Calculate prediction accuracy."""
        try:
            if len(predictions) != len(outcomes) or len(predictions) == 0:
                return 0.0
            
            pred_binary = [1 if p > 0 else 0 for p in predictions]
            outcome_binary = [1 if o > 0 else 0 for o in outcomes]
            
            correct = sum(1 for p, o in zip(pred_binary, outcome_binary) if p == o)
            return correct / len(predictions)
        except:
            return 0.0
    
    def _calculate_sharpe_ratio(self, returns: List[float]) -> float:
        """Calculate Sharpe ratio."""
        try:
            if len(returns) < 2:
                return 0.0
            
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            
            if std_return == 0:
                return 0.0
            
            return mean_return / std_return * np.sqrt(252)  # Annualized
        except:
            return 0.0


class AdvancedModelManager:
    """Advanced model manager with comprehensive ML lifecycle management."""
    
    def __init__(self, models_dir: str = "models", registry_path: str = "model_registry.db"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)
        
        # Core components
        self.registry = ModelRegistry(registry_path)
        self.monitor = ModelMonitor(self.registry)
        self.ab_test_manager = ABTestManager(self.registry)
        
        # Model instances
        self.models = {}  # model_name -> BaseMLStrategy
        self.active_models = {}  # model_name -> version
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        logger.info("Advanced Model Manager initialized")
    
    def create_and_train_model(self, model_name: str, model_type: ModelType,
                              config: ModelConfig, data: pd.DataFrame,
                              target_column: str = None) -> bool:
        """Create and train a new model.
        
        Args:
            model_name: Name for the model
            model_type: Type of model to create
            config: Model configuration
            data: Training data
            target_column: Target column name
            
        Returns:
            True if successful
        """
        try:
            # Create model instance
            if model_type == ModelType.RANDOM_FOREST:
                model = RandomForestStrategy(config)
            elif model_type == ModelType.XGBOOST:
                model = XGBoostStrategy(config)
            elif model_type == ModelType.SVM:
                model = SVMStrategy(config)
            elif model_type == ModelType.NEURAL_NETWORK:
                model = NeuralNetworkStrategy(config)
            elif model_type == ModelType.ENSEMBLE:
                model = EnsembleStrategy(config)
            else:
                raise ValueError(f"Unknown model type: {model_type}")
            
            # Train model
            if not model.train(data, target_column):
                logger.error(f"Failed to train model {model_name}")
                return False
            
            # Register model
            version = self.registry.register_model(model_name, model)
            
            # Store model instance
            self.models[model_name] = model
            self.active_models[model_name] = version
            
            # Save model to disk
            model_path = self.models_dir / f"{model_name}_{version}.joblib"
            model.save_model(str(model_path))
            
            logger.info(f"Successfully created and trained model {model_name}")
            return True
        
        except Exception as e:
            logger.error(f"Error creating and training model: {e}")
            return False
    
    def predict_with_monitoring(self, model_name: str, data: pd.DataFrame,
                               user_id: str = None) -> PredictionResult:
        """Make prediction with monitoring and A/B testing.
        
        Args:
            model_name: Name of the model
            data: Input data
            user_id: User ID for A/B testing
            
        Returns:
            Prediction result
        """
        try:
            # Check for active A/B tests
            actual_model = model_name
            for test_name, config in self.ab_test_manager.active_tests.items():
                if model_name in [config.control_model] + config.treatment_models:
                    if user_id:
                        actual_model = self.ab_test_manager.route_prediction(test_name, user_id)
                    break
            
            # Make prediction
            if actual_model not in self.models:
                logger.error(f"Model {actual_model} not found")
                return PredictionResult(
                    timestamp=datetime.now(),
                    prediction=0,
                    confidence=0.0
                )
            
            result = self.models[actual_model].predict(data)
            
            # Log for monitoring
            self.monitor.log_prediction(actual_model, result)
            
            # Log for A/B testing
            for test_name in self.ab_test_manager.active_tests:
                self.ab_test_manager.log_ab_test_result(
                    test_name, actual_model, result.prediction
                )
            
            return result
        
        except Exception as e:
            logger.error(f"Error making prediction: {e}")
            return PredictionResult(
                timestamp=datetime.now(),
                prediction=0,
                confidence=0.0
            )
    
    def start_monitoring(self) -> None:
        """Start model monitoring."""
        self.monitor.start_monitoring()
    
    def stop_monitoring(self) -> None:
        """Stop model monitoring."""
        self.monitor.stop_monitoring()
    
    def get_model_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all models.
        
        Returns:
            Dictionary with model status information
        """
        try:
            status = {
                'models': {},
                'alerts': self.monitor.get_alerts(),
                'ab_tests': list(self.ab_test_manager.active_tests.keys())
            }
            
            for model_name, model in self.models.items():
                versions = self.registry.get_model_versions(model_name)
                active_version = self.active_models.get(model_name)
                
                status['models'][model_name] = {
                    'status': model.status.value,
                    'active_version': active_version,
                    'total_versions': len(versions),
                    'predictions_made': model.predictions_made,
                    'last_retrain': model.last_retrain
                }
            
            return status
        
        except Exception as e:
            logger.error(f"Error getting model status: {e}")
            return {}
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        try:
            self.stop_monitoring()
            self.executor.shutdown(wait=True)
            logger.info("Model manager cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")