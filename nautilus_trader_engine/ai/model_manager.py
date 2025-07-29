"""
ML Model Management Framework
Comprehensive model lifecycle management for trading AI systems
"""

import asyncio
import json
import os
import pickle
import time
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable
from pathlib import Path
import logging
import threading

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False
    joblib = None

# Import A/B testing and versioning systems
from .ab_testing import ABTestManager, TestConfiguration, ModelVariant, TestMetric, TestResult
from .model_versioning import ModelVersioningSystem, ModelMetadata as VersioningMetadata, ModelType as VersioningModelType


class ModelType(Enum):
    """Types of ML models supported"""
    SKLEARN = "sklearn"
    TENSORFLOW = "tensorflow"
    PYTORCH = "pytorch"
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    CUSTOM = "custom"


class ModelStatus(Enum):
    """Model lifecycle status"""
    TRAINING = "training"
    TRAINED = "trained"
    VALIDATING = "validating"
    VALIDATED = "validated"
    DEPLOYED = "deployed"
    DEPRECATED = "deprecated"
    FAILED = "failed"


class ModelPurpose(Enum):
    """Purpose/use case of the model"""
    PRICE_PREDICTION = "price_prediction"
    TREND_DETECTION = "trend_detection"
    ANOMALY_DETECTION = "anomaly_detection"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    RISK_ASSESSMENT = "risk_assessment"
    PATTERN_RECOGNITION = "pattern_recognition"
    VOLUME_PREDICTION = "volume_prediction"
    VOLATILITY_PREDICTION = "volatility_prediction"


@dataclass
class ModelConfig:
    """Configuration for ML model"""
    name: str
    version: str
    model_type: ModelType
    purpose: ModelPurpose
    description: str = ""
    
    # Training configuration
    training_params: Dict[str, Any] = field(default_factory=dict)
    validation_params: Dict[str, Any] = field(default_factory=dict)
    
    # Feature configuration
    input_features: List[str] = field(default_factory=list)
    output_features: List[str] = field(default_factory=list)
    feature_preprocessing: Dict[str, Any] = field(default_factory=dict)
    
    # Performance thresholds
    min_accuracy: float = 0.7
    max_latency_ms: float = 100.0
    
    # Deployment configuration
    auto_deploy: bool = False
    a_b_test_enabled: bool = False
    canary_percentage: float = 10.0
    
    # Retraining configuration
    auto_retrain: bool = True
    retrain_threshold: float = 0.05  # Performance degradation threshold
    retrain_interval_hours: int = 24
    
    # Resource limits
    max_memory_mb: int = 1024
    max_cpu_cores: int = 2


@dataclass
class ModelMetadata:
    """Metadata for trained model"""
    config: ModelConfig
    
    # Training metadata
    training_start_time: float = 0.0
    training_end_time: float = 0.0
    training_duration_seconds: float = 0.0
    training_samples: int = 0
    
    # Performance metrics
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    auc_score: float = 0.0
    custom_metrics: Dict[str, float] = field(default_factory=dict)
    
    # Model artifacts
    model_path: str = ""
    model_size_bytes: int = 0
    model_hash: str = ""
    
    # Deployment metadata
    status: ModelStatus = ModelStatus.TRAINING
    deployment_time: float = 0.0
    last_prediction_time: float = 0.0
    prediction_count: int = 0
    
    # Performance tracking
    recent_accuracy: float = 0.0
    performance_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        if self.training_start_time == 0.0:
            self.training_start_time = time.time()


class ModelInterface(ABC):
    """Abstract interface for ML models"""
    
    @abstractmethod
    def train(self, X: Any, y: Any, **kwargs) -> Dict[str, Any]:
        """Train the model"""
        pass
    
    @abstractmethod
    def predict(self, X: Any) -> Any:
        """Make predictions"""
        pass
    
    @abstractmethod
    def predict_proba(self, X: Any) -> Any:
        """Get prediction probabilities (if applicable)"""
        pass
    
    @abstractmethod
    def save(self, path: str) -> bool:
        """Save model to disk"""
        pass
    
    @abstractmethod
    def load(self, path: str) -> bool:
        """Load model from disk"""
        pass
    
    @abstractmethod
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores"""
        pass


class SklearnModelWrapper(ModelInterface):
    """Wrapper for scikit-learn models"""
    
    def __init__(self, model_class, **model_params):
        self.model_class = model_class
        self.model_params = model_params
        self.model = None
        self.is_trained = False
    
    def train(self, X: Any, y: Any, **kwargs) -> Dict[str, Any]:
        """Train sklearn model"""
        try:
            # Initialize model
            self.model = self.model_class(**self.model_params)
            
            # Train model
            start_time = time.time()
            self.model.fit(X, y)
            training_time = time.time() - start_time
            
            self.is_trained = True
            
            # Calculate basic metrics
            train_score = self.model.score(X, y) if hasattr(self.model, 'score') else 0.0
            
            return {
                'training_time': training_time,
                'train_score': train_score,
                'model_params': self.model.get_params() if hasattr(self.model, 'get_params') else {}
            }
        
        except Exception as e:
            raise RuntimeError(f"Training failed: {e}")
    
    def predict(self, X: Any) -> Any:
        """Make predictions"""
        if not self.is_trained or self.model is None:
            raise RuntimeError("Model not trained")
        
        return self.model.predict(X)
    
    def predict_proba(self, X: Any) -> Any:
        """Get prediction probabilities"""
        if not self.is_trained or self.model is None:
            raise RuntimeError("Model not trained")
        
        if hasattr(self.model, 'predict_proba'):
            return self.model.predict_proba(X)
        else:
            raise NotImplementedError("Model does not support probability predictions")
    
    def save(self, path: str) -> bool:
        """Save model using joblib"""
        if not JOBLIB_AVAILABLE:
            raise ImportError("joblib is required for saving sklearn models")
        
        try:
            joblib.dump(self.model, path)
            return True
        except Exception as e:
            logging.error(f"Failed to save model: {e}")
            return False
    
    def load(self, path: str) -> bool:
        """Load model using joblib"""
        if not JOBLIB_AVAILABLE:
            raise ImportError("joblib is required for loading sklearn models")
        
        try:
            self.model = joblib.load(path)
            self.is_trained = True
            return True
        except Exception as e:
            logging.error(f"Failed to load model: {e}")
            return False
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance if available"""
        if not self.is_trained or self.model is None:
            return {}
        
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            return {f'feature_{i}': float(imp) for i, imp in enumerate(importances)}
        elif hasattr(self.model, 'coef_'):
            coefficients = self.model.coef_
            if coefficients.ndim == 1:
                return {f'feature_{i}': float(coef) for i, coef in enumerate(coefficients)}
            else:
                # Multi-class case - return average absolute coefficients
                avg_coef = np.mean(np.abs(coefficients), axis=0)
                return {f'feature_{i}': float(coef) for i, coef in enumerate(avg_coef)}
        
        return {}


class ModelManager:
    """
    Comprehensive ML model management system
    
    Features:
    - Model versioning and lifecycle management
    - A/B testing framework
    - Automated retraining
    - Performance monitoring
    - Model deployment and rollback
    - Feature importance tracking
    """
    
    def __init__(self, 
                 models_directory: str = "models",
                 enable_monitoring: bool = True,
                 enable_auto_retrain: bool = True,
                 enable_ab_testing: bool = True,
                 enable_versioning: bool = True):
        
        self.models_directory = Path(models_directory)
        self.models_directory.mkdir(exist_ok=True)
        
        self.enable_monitoring = enable_monitoring
        self.enable_auto_retrain = enable_auto_retrain
        self.enable_ab_testing = enable_ab_testing
        self.enable_versioning = enable_versioning
        
        # Model registry
        self._models: Dict[str, ModelMetadata] = {}
        self._deployed_models: Dict[str, ModelInterface] = {}
        self._model_configs: Dict[str, ModelConfig] = {}
        
        # A/B testing integration
        self._ab_test_manager: Optional[ABTestManager] = None
        self._active_ab_tests: Dict[str, str] = {}  # model_id -> test_id
        
        # Versioning integration
        self._versioning_system: Optional[ModelVersioningSystem] = None
        
        # Performance monitoring
        self._performance_history: Dict[str, List[Dict[str, Any]]] = {}
        
        # Background tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._retraining_task: Optional[asyncio.Task] = None
        self._ab_testing_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Thread safety
        self._lock = threading.RLock()
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start model manager and background tasks"""
        if self._running:
            return
        
        self._running = True
        
        # Initialize A/B testing system
        if self.enable_ab_testing:
            self._ab_test_manager = ABTestManager()
            await self._ab_test_manager.start()
        
        # Initialize versioning system
        if self.enable_versioning:
            versioning_path = self.models_directory / "versioning"
            self._versioning_system = ModelVersioningSystem(str(versioning_path))
        
        # Load existing models
        await self._load_existing_models()
        
        # Start background tasks
        if self.enable_monitoring:
            self._monitoring_task = asyncio.create_task(self._monitoring_worker())
        
        if self.enable_auto_retrain:
            self._retraining_task = asyncio.create_task(self._retraining_worker())
        
        if self.enable_ab_testing:
            self._ab_testing_task = asyncio.create_task(self._ab_testing_worker())
        
        self.logger.info("ModelManager started with A/B testing and versioning")
    
    async def stop(self):
        """Stop model manager and cleanup"""
        self._running = False
        
        # Cancel background tasks
        if self._monitoring_task:
            self._monitoring_task.cancel()
        if self._retraining_task:
            self._retraining_task.cancel()
        if self._ab_testing_task:
            self._ab_testing_task.cancel()
        
        # Stop A/B testing system
        if self._ab_test_manager:
            await self._ab_test_manager.stop()
        
        self.logger.info("ModelManager stopped")
    
    async def register_model(self, config: ModelConfig) -> str:
        """Register a new model configuration"""
        with self._lock:
            model_id = f"{config.name}_{config.version}"
            
            if model_id in self._model_configs:
                raise ValueError(f"Model {model_id} already registered")
            
            self._model_configs[model_id] = config
            
            # Initialize metadata
            metadata = ModelMetadata(config=config)
            self._models[model_id] = metadata
            
            # Save configuration
            await self._save_model_config(model_id, config)
            
            self.logger.info(f"Registered model: {model_id}")
            return model_id
    
    async def train_model(self, 
                         model_id: str, 
                         training_data: Any, 
                         labels: Any,
                         validation_data: Optional[Any] = None,
                         validation_labels: Optional[Any] = None) -> Dict[str, Any]:
        """Train a registered model"""
        with self._lock:
            if model_id not in self._model_configs:
                raise ValueError(f"Model {model_id} not registered")
            
            config = self._model_configs[model_id]
            metadata = self._models[model_id]
            
            # Update status
            metadata.status = ModelStatus.TRAINING
            metadata.training_start_time = time.time()
            
            try:
                # Create model instance
                model = self._create_model_instance(config)
                
                # Train model
                training_results = model.train(training_data, labels, **config.training_params)
                
                # Update metadata
                metadata.training_end_time = time.time()
                metadata.training_duration_seconds = metadata.training_end_time - metadata.training_start_time
                metadata.training_samples = len(training_data) if hasattr(training_data, '__len__') else 0
                
                # Validate model if validation data provided
                if validation_data is not None and validation_labels is not None:
                    validation_results = await self._validate_model(model, validation_data, validation_labels, config)
                    
                    # Update metadata with validation results
                    metadata.accuracy = validation_results.get('accuracy', 0.0)
                    metadata.precision = validation_results.get('precision', 0.0)
                    metadata.recall = validation_results.get('recall', 0.0)
                    metadata.f1_score = validation_results.get('f1_score', 0.0)
                    metadata.auc_score = validation_results.get('auc_score', 0.0)
                    metadata.custom_metrics = validation_results.get('custom_metrics', {})
                    
                    # Check if model meets minimum requirements
                    if metadata.accuracy >= config.min_accuracy:
                        metadata.status = ModelStatus.VALIDATED
                    else:
                        metadata.status = ModelStatus.FAILED
                        raise ValueError(f"Model accuracy {metadata.accuracy} below threshold {config.min_accuracy}")
                else:
                    metadata.status = ModelStatus.TRAINED
                
                # Save model
                model_path = self._get_model_path(model_id)
                if model.save(str(model_path)):
                    metadata.model_path = str(model_path)
                    metadata.model_size_bytes = model_path.stat().st_size
                    metadata.model_hash = self._calculate_file_hash(model_path)
                
                # Save metadata
                await self._save_model_metadata(model_id, metadata)
                
                # Create model version if versioning is enabled
                version = None
                if self.enable_versioning and self._versioning_system:
                    try:
                        version = await self.create_model_version(
                            model_id, 
                            model, 
                            description=f"Training completed with accuracy: {metadata.accuracy:.3f}"
                        )
                    except Exception as e:
                        self.logger.warning(f"Failed to create model version: {e}")
                
                # Auto-deploy if configured
                if config.auto_deploy and metadata.status == ModelStatus.VALIDATED:
                    await self.deploy_model(model_id)
                
                results = {
                    'model_id': model_id,
                    'version': version,
                    'status': metadata.status.value,
                    'training_time': metadata.training_duration_seconds,
                    'accuracy': metadata.accuracy,
                    'model_size_bytes': metadata.model_size_bytes
                }
                results.update(training_results)
                
                self.logger.info(f"Model {model_id} training completed: {metadata.status.value}")
                return results
            
            except Exception as e:
                metadata.status = ModelStatus.FAILED
                await self._save_model_metadata(model_id, metadata)
                self.logger.error(f"Model {model_id} training failed: {e}")
                raise
    
    async def deploy_model(self, model_id: str, canary_percentage: Optional[float] = None) -> bool:
        """Deploy a trained model"""
        with self._lock:
            if model_id not in self._models:
                raise ValueError(f"Model {model_id} not found")
            
            metadata = self._models[model_id]
            config = self._model_configs[model_id]
            
            if metadata.status not in [ModelStatus.TRAINED, ModelStatus.VALIDATED]:
                raise ValueError(f"Model {model_id} not ready for deployment (status: {metadata.status})")
            
            try:
                # Load model
                model = self._create_model_instance(config)
                if not model.load(metadata.model_path):
                    raise RuntimeError("Failed to load model")
                
                # Deploy model
                if config.a_b_test_enabled:
                    # Deploy as A/B test
                    percentage = canary_percentage or config.canary_percentage
                    await self._deploy_ab_test(model_id, model, percentage)
                else:
                    # Full deployment
                    self._deployed_models[model_id] = model
                
                # Update metadata
                metadata.status = ModelStatus.DEPLOYED
                metadata.deployment_time = time.time()
                await self._save_model_metadata(model_id, metadata)
                
                self.logger.info(f"Model {model_id} deployed successfully")
                return True
            
            except Exception as e:
                self.logger.error(f"Model {model_id} deployment failed: {e}")
                return False
    
    async def predict(self, model_id: str, input_data: Any, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Make prediction using deployed model with A/B testing support"""
        with self._lock:
            # Check if model is in A/B test
            if model_id in self._active_ab_tests and self._ab_test_manager and user_id:
                test_id = self._active_ab_tests[model_id]
                variant_id = await self._ab_test_manager.assign_variant(test_id, user_id)
                
                # Use the assigned variant for prediction
                # In practice, you'd map variant_id to actual model_id
                actual_model_id = model_id  # Simplified for now
            else:
                actual_model_id = model_id
            
            if actual_model_id not in self._deployed_models:
                raise ValueError(f"Model {actual_model_id} not deployed")
            
            model = self._deployed_models[actual_model_id]
            metadata = self._models[actual_model_id]
            
            try:
                start_time = time.time()
                
                # Make prediction
                prediction = model.predict(input_data)
                
                # Get probabilities if available
                probabilities = None
                try:
                    probabilities = model.predict_proba(input_data)
                except (NotImplementedError, AttributeError):
                    pass
                
                prediction_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                
                # Update metadata
                metadata.last_prediction_time = time.time()
                metadata.prediction_count += 1
                
                # Check latency threshold
                config = self._model_configs[actual_model_id]
                if prediction_time > config.max_latency_ms:
                    self.logger.warning(f"Model {actual_model_id} prediction latency {prediction_time:.2f}ms exceeds threshold {config.max_latency_ms}ms")
                
                result = {
                    'model_id': actual_model_id,
                    'prediction': prediction.tolist() if hasattr(prediction, 'tolist') else prediction,
                    'probabilities': probabilities.tolist() if probabilities is not None and hasattr(probabilities, 'tolist') else probabilities,
                    'prediction_time_ms': prediction_time,
                    'timestamp': time.time()
                }
                
                # Record A/B test result if applicable
                if model_id in self._active_ab_tests and user_id:
                    await self.record_ab_test_result(
                        model_id, 
                        user_id, 
                        {'prediction_time_ms': prediction_time},
                        {'prediction': result['prediction']}
                    )
                
                return result
            
            except Exception as e:
                self.logger.error(f"Prediction failed for model {actual_model_id}: {e}")
                raise
    
    async def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """Get comprehensive model information"""
        with self._lock:
            if model_id not in self._models:
                raise ValueError(f"Model {model_id} not found")
            
            metadata = self._models[model_id]
            config = self._model_configs[model_id]
            
            # Get feature importance if model is deployed
            feature_importance = {}
            if model_id in self._deployed_models:
                try:
                    feature_importance = self._deployed_models[model_id].get_feature_importance()
                except Exception as e:
                    self.logger.warning(f"Could not get feature importance for {model_id}: {e}")
            
            return {
                'model_id': model_id,
                'config': {
                    'name': config.name,
                    'version': config.version,
                    'type': config.model_type.value,
                    'purpose': config.purpose.value,
                    'description': config.description
                },
                'metadata': {
                    'status': metadata.status.value,
                    'training_duration': metadata.training_duration_seconds,
                    'training_samples': metadata.training_samples,
                    'accuracy': metadata.accuracy,
                    'precision': metadata.precision,
                    'recall': metadata.recall,
                    'f1_score': metadata.f1_score,
                    'model_size_bytes': metadata.model_size_bytes,
                    'deployment_time': metadata.deployment_time,
                    'prediction_count': metadata.prediction_count,
                    'last_prediction_time': metadata.last_prediction_time
                },
                'feature_importance': feature_importance,
                'performance_history': metadata.performance_history[-10:]  # Last 10 entries
            }
    
    async def list_models(self, status_filter: Optional[ModelStatus] = None) -> List[Dict[str, Any]]:
        """List all registered models"""
        with self._lock:
            models = []
            
            for model_id, metadata in self._models.items():
                if status_filter is None or metadata.status == status_filter:
                    config = self._model_configs[model_id]
                    
                    models.append({
                        'model_id': model_id,
                        'name': config.name,
                        'version': config.version,
                        'type': config.model_type.value,
                        'purpose': config.purpose.value,
                        'status': metadata.status.value,
                        'accuracy': metadata.accuracy,
                        'deployment_time': metadata.deployment_time,
                        'prediction_count': metadata.prediction_count
                    })
            
            return sorted(models, key=lambda x: x['deployment_time'], reverse=True)
    
    # A/B Testing Integration Methods
    
    async def create_ab_test(self, 
                           test_name: str,
                           model_variants: List[Dict[str, Any]],
                           test_metrics: List[Dict[str, Any]],
                           traffic_split_method: str = "random",
                           minimum_sample_size: int = 1000,
                           maximum_duration_days: int = 30) -> str:
        """Create A/B test for model comparison"""
        if not self.enable_ab_testing or not self._ab_test_manager:
            raise RuntimeError("A/B testing not enabled")
        
        try:
            # Convert model variants
            variants = []
            for i, variant_data in enumerate(model_variants):
                model_id = variant_data['model_id']
                version = variant_data.get('version', 'latest')
                traffic_percentage = variant_data.get('traffic_percentage', 100.0 / len(model_variants))
                
                # Validate model exists
                if model_id not in self._models:
                    raise ValueError(f"Model {model_id} not found")
                
                variant = ModelVariant(
                    variant_id=f"variant_{i}",
                    model_id=model_id,
                    model_version=version,
                    traffic_percentage=traffic_percentage,
                    description=variant_data.get('description', f'Variant {i}')
                )
                variants.append(variant)
            
            # Convert test metrics
            metrics = []
            for metric_data in test_metrics:
                metric = TestMetric(
                    name=metric_data['name'],
                    description=metric_data.get('description', ''),
                    metric_type=metric_data.get('type', 'continuous'),
                    higher_is_better=metric_data.get('higher_is_better', True),
                    minimum_detectable_effect=metric_data.get('min_effect', 0.05),
                    statistical_power=metric_data.get('power', 0.8),
                    significance_level=metric_data.get('alpha', 0.05)
                )
                metrics.append(metric)
            
            # Create test configuration
            from .ab_testing import TrafficSplitMethod
            split_method = TrafficSplitMethod(traffic_split_method)
            
            test_config = TestConfiguration(
                test_id=f"test_{int(time.time())}",
                name=test_name,
                description=f"A/B test for models: {[v.model_id for v in variants]}",
                variants=variants,
                metrics=metrics,
                traffic_split_method=split_method,
                minimum_sample_size=minimum_sample_size,
                maximum_duration_days=maximum_duration_days
            )
            
            # Create test
            test_id = await self._ab_test_manager.create_test(test_config)
            
            # Track active test
            for variant in variants:
                self._active_ab_tests[variant.model_id] = test_id
            
            self.logger.info(f"Created A/B test {test_id} for models: {[v.model_id for v in variants]}")
            return test_id
            
        except Exception as e:
            self.logger.error(f"Failed to create A/B test: {e}")
            raise
    
    async def start_ab_test(self, test_id: str):
        """Start an A/B test"""
        if not self._ab_test_manager:
            raise RuntimeError("A/B testing not enabled")
        
        await self._ab_test_manager.start_test(test_id)
        self.logger.info(f"Started A/B test: {test_id}")
    
    async def stop_ab_test(self, test_id: str, reason: str = "Manual stop") -> Dict[str, Any]:
        """Stop an A/B test and get results"""
        if not self._ab_test_manager:
            raise RuntimeError("A/B testing not enabled")
        
        results = await self._ab_test_manager.stop_test(test_id, reason)
        
        # Remove from active tests
        models_to_remove = [model_id for model_id, tid in self._active_ab_tests.items() if tid == test_id]
        for model_id in models_to_remove:
            del self._active_ab_tests[model_id]
        
        self.logger.info(f"Stopped A/B test {test_id}: {reason}")
        return results
    
    async def get_ab_test_results(self, test_id: str) -> Dict[str, Any]:
        """Get A/B test analysis results"""
        if not self._ab_test_manager:
            raise RuntimeError("A/B testing not enabled")
        
        return await self._ab_test_manager.analyze_test(test_id)
    
    async def record_ab_test_result(self, 
                                  model_id: str, 
                                  user_id: str, 
                                  metrics: Dict[str, float],
                                  metadata: Dict[str, Any] = None):
        """Record A/B test result"""
        if not self._ab_test_manager or model_id not in self._active_ab_tests:
            return  # No active test for this model
        
        test_id = self._active_ab_tests[model_id]
        
        # Get variant assignment
        variant_id = await self._ab_test_manager.assign_variant(test_id, user_id)
        
        # Record result
        from datetime import datetime
        result = TestResult(
            test_id=test_id,
            variant_id=variant_id,
            user_id=user_id,
            timestamp=datetime.now(),
            metrics=metrics,
            metadata=metadata or {}
        )
        
        await self._ab_test_manager.record_result(result)
    
    # Model Versioning Integration Methods
    
    async def create_model_version(self, 
                                 model_id: str, 
                                 model_artifact: Any,
                                 version: Optional[str] = None,
                                 description: str = "",
                                 created_by: str = "system") -> str:
        """Create a new model version"""
        if not self.enable_versioning or not self._versioning_system:
            raise RuntimeError("Model versioning not enabled")
        
        try:
            # Get model config
            if model_id not in self._model_configs:
                raise ValueError(f"Model {model_id} not registered")
            
            config = self._model_configs[model_id]
            
            # Convert to versioning metadata
            versioning_metadata = VersioningMetadata(
                model_id=model_id,
                version=version or "auto",
                name=config.name,
                description=description,
                model_type=self._convert_model_type(config.model_type),
                framework=self._get_framework_name(config.model_type),
                created_at=datetime.now(),
                created_by=created_by,
                tags=[config.purpose.value],
                parameters=config.training_params,
                dependencies=[]
            )
            
            # Register with versioning system
            actual_version = await self._versioning_system.register_model(
                model_id, model_artifact, versioning_metadata, version
            )
            
            self.logger.info(f"Created model version {model_id}:{actual_version}")
            return actual_version
            
        except Exception as e:
            self.logger.error(f"Failed to create model version: {e}")
            raise
    
    async def promote_model_version(self, model_id: str, version: str) -> bool:
        """Promote model version to next stage"""
        if not self._versioning_system:
            raise RuntimeError("Model versioning not enabled")
        
        return await self._versioning_system.promote_model(model_id, version)
    
    async def rollback_model(self, model_id: str, target_version: Optional[str] = None) -> bool:
        """Rollback model to previous version"""
        if not self._versioning_system:
            raise RuntimeError("Model versioning not enabled")
        
        success = await self._versioning_system.rollback_model(model_id, target_version)
        
        if success:
            # Update deployed model if it exists
            if model_id in self._deployed_models:
                # Reload model from versioning system
                new_model = await self._versioning_system.get_model(model_id)
                if new_model:
                    # Create wrapper for the rolled-back model
                    config = self._model_configs[model_id]
                    model_wrapper = self._create_model_instance(config)
                    model_wrapper.model = new_model
                    model_wrapper.is_trained = True
                    
                    self._deployed_models[model_id] = model_wrapper
                    
                    self.logger.info(f"Reloaded rolled-back model {model_id}")
        
        return success
    
    async def get_model_versions(self, model_id: str) -> List[Dict[str, Any]]:
        """Get all versions of a model"""
        if not self._versioning_system:
            return []
        
        return await self._versioning_system.list_model_versions(model_id)
    
    async def compare_model_versions(self, model_id: str, version1: str, version2: str) -> Dict[str, Any]:
        """Compare two model versions"""
        if not self._versioning_system:
            raise RuntimeError("Model versioning not enabled")
        
        return await self._versioning_system.compare_models(model_id, version1, version2)
    
    # Background Workers
    
    async def _ab_testing_worker(self):
        """Background worker for A/B testing monitoring"""
        while self._running:
            try:
                if self._ab_test_manager:
                    # Monitor active tests for early stopping conditions
                    for model_id, test_id in list(self._active_ab_tests.items()):
                        try:
                            analysis = await self._ab_test_manager.analyze_test(test_id)
                            
                            # Check for early stopping conditions
                            if self._should_stop_test_early(analysis):
                                await self.stop_ab_test(test_id, "Early stopping - significant results")
                        
                        except Exception as e:
                            self.logger.error(f"Error monitoring A/B test {test_id}: {e}")
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"A/B testing worker error: {e}")
                await asyncio.sleep(60)
    
    def _should_stop_test_early(self, analysis: Dict[str, Any]) -> bool:
        """Determine if A/B test should be stopped early"""
        try:
            # Check if we have enough samples
            if analysis.get('total_samples', 0) < 1000:
                return False
            
            # Check for significant results
            statistical_tests = analysis.get('statistical_tests', {})
            significant_count = sum(1 for test in statistical_tests.values() if test.get('is_significant', False))
            
            # Stop if majority of tests are significant
            return significant_count > len(statistical_tests) / 2
            
        except Exception:
            return False
    
    def _convert_model_type(self, model_type: ModelType) -> VersioningModelType:
        """Convert ModelType to VersioningModelType"""
        type_mapping = {
            ModelType.SKLEARN: VersioningModelType.CLASSIFICATION,  # Default mapping
            ModelType.TENSORFLOW: VersioningModelType.DEEP_LEARNING,
            ModelType.PYTORCH: VersioningModelType.DEEP_LEARNING,
            ModelType.XGBOOST: VersioningModelType.CLASSIFICATION,
            ModelType.LIGHTGBM: VersioningModelType.CLASSIFICATION,
            ModelType.CUSTOM: VersioningModelType.CLASSIFICATION
        }
        return type_mapping.get(model_type, VersioningModelType.CLASSIFICATION)
    
    def _get_framework_name(self, model_type: ModelType) -> str:
        """Get framework name from model type"""
        framework_mapping = {
            ModelType.SKLEARN: "scikit-learn",
            ModelType.TENSORFLOW: "tensorflow",
            ModelType.PYTORCH: "pytorch",
            ModelType.XGBOOST: "xgboost",
            ModelType.LIGHTGBM: "lightgbm",
            ModelType.CUSTOM: "custom"
        }
        return framework_mapping.get(model_type, "unknown")
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive model manager statistics"""
        stats = {
            'model_manager': {
                'total_models': len(self._models),
                'deployed_models': len(self._deployed_models),
                'registered_configs': len(self._model_configs),
                'running': self._running,
                'features': {
                    'monitoring_enabled': self.enable_monitoring,
                    'auto_retrain_enabled': self.enable_auto_retrain,
                    'ab_testing_enabled': self.enable_ab_testing,
                    'versioning_enabled': self.enable_versioning
                }
            }
        }
        
        # A/B testing statistics
        if self.enable_ab_testing and self._ab_test_manager:
            stats['ab_testing'] = {
                'active_tests': len(self._active_ab_tests),
                'models_in_testing': list(self._active_ab_tests.keys())
            }
        
        # Versioning statistics
        if self.enable_versioning and self._versioning_system:
            stats['versioning'] = self._versioning_system.get_registry_stats()
        
        # Model status distribution
        status_counts = {}
        for metadata in self._models.values():
            status = metadata.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        stats['model_status_distribution'] = status_counts
        
        # Performance summary
        total_predictions = sum(m.prediction_count for m in self._models.values())
        avg_accuracy = sum(m.accuracy for m in self._models.values()) / len(self._models) if self._models else 0
        
        stats['performance_summary'] = {
            'total_predictions': total_predictions,
            'average_accuracy': avg_accuracy,
            'models_directory': str(self.models_directory)
        }
        
        return stats
    
    def _create_model_instance(self, config: ModelConfig) -> ModelInterface:
        """Create model instance based on configuration"""
        if config.model_type == ModelType.SKLEARN:
            # This is a simplified example - in practice, you'd have a registry
            # of model classes and their parameters
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.linear_model import LogisticRegression
            
            # Default to RandomForest for demonstration
            model_class = RandomForestClassifier
            return SklearnModelWrapper(model_class, **config.training_params)
        
        else:
            raise NotImplementedError(f"Model type {config.model_type} not implemented")
    
    async def _validate_model(self, model: ModelInterface, X_val: Any, y_val: Any, config: ModelConfig) -> Dict[str, Any]:
        """Validate model performance"""
        try:
            predictions = model.predict(X_val)
            
            # Calculate basic metrics (simplified - would use sklearn.metrics in practice)
            if NUMPY_AVAILABLE:
                accuracy = np.mean(predictions == y_val) if hasattr(y_val, '__len__') else 0.0
            else:
                # Fallback calculation
                correct = sum(1 for p, t in zip(predictions, y_val) if p == t)
                accuracy = correct / len(y_val) if len(y_val) > 0 else 0.0
            
            return {
                'accuracy': accuracy,
                'precision': accuracy,  # Simplified
                'recall': accuracy,     # Simplified
                'f1_score': accuracy,   # Simplified
                'auc_score': accuracy,  # Simplified
                'custom_metrics': {}
            }
        
        except Exception as e:
            self.logger.error(f"Model validation failed: {e}")
            return {
                'accuracy': 0.0,
                'precision': 0.0,
                'recall': 0.0,
                'f1_score': 0.0,
                'auc_score': 0.0,
                'custom_metrics': {}
            }
    
    def _get_model_path(self, model_id: str) -> Path:
        """Get file path for model storage"""
        return self.models_directory / f"{model_id}.joblib"
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    async def _save_model_config(self, model_id: str, config: ModelConfig):
        """Save model configuration to disk"""
        config_path = self.models_directory / f"{model_id}_config.json"
        
        # Convert config to dict for JSON serialization
        config_dict = {
            'name': config.name,
            'version': config.version,
            'model_type': config.model_type.value,
            'purpose': config.purpose.value,
            'description': config.description,
            'training_params': config.training_params,
            'validation_params': config.validation_params,
            'input_features': config.input_features,
            'output_features': config.output_features,
            'feature_preprocessing': config.feature_preprocessing,
            'min_accuracy': config.min_accuracy,
            'max_latency_ms': config.max_latency_ms,
            'auto_deploy': config.auto_deploy,
            'a_b_test_enabled': config.a_b_test_enabled,
            'canary_percentage': config.canary_percentage,
            'auto_retrain': config.auto_retrain,
            'retrain_threshold': config.retrain_threshold,
            'retrain_interval_hours': config.retrain_interval_hours,
            'max_memory_mb': config.max_memory_mb,
            'max_cpu_cores': config.max_cpu_cores
        }
        
        with open(config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    async def _save_model_metadata(self, model_id: str, metadata: ModelMetadata):
        """Save model metadata to disk"""
        metadata_path = self.models_directory / f"{model_id}_metadata.json"
        
        # Convert metadata to dict for JSON serialization
        metadata_dict = {
            'training_start_time': metadata.training_start_time,
            'training_end_time': metadata.training_end_time,
            'training_duration_seconds': metadata.training_duration_seconds,
            'training_samples': metadata.training_samples,
            'accuracy': metadata.accuracy,
            'precision': metadata.precision,
            'recall': metadata.recall,
            'f1_score': metadata.f1_score,
            'auc_score': metadata.auc_score,
            'custom_metrics': metadata.custom_metrics,
            'model_path': metadata.model_path,
            'model_size_bytes': metadata.model_size_bytes,
            'model_hash': metadata.model_hash,
            'status': metadata.status.value,
            'deployment_time': metadata.deployment_time,
            'last_prediction_time': metadata.last_prediction_time,
            'prediction_count': metadata.prediction_count,
            'recent_accuracy': metadata.recent_accuracy,
            'performance_history': metadata.performance_history
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata_dict, f, indent=2)
    
    async def _load_existing_models(self):
        """Load existing models from disk"""
        try:
            for config_file in self.models_directory.glob("*_config.json"):
                model_id = config_file.stem.replace("_config", "")
                
                # Load configuration
                with open(config_file, 'r') as f:
                    config_dict = json.load(f)
                
                config = ModelConfig(
                    name=config_dict['name'],
                    version=config_dict['version'],
                    model_type=ModelType(config_dict['model_type']),
                    purpose=ModelPurpose(config_dict['purpose']),
                    description=config_dict.get('description', ''),
                    training_params=config_dict.get('training_params', {}),
                    validation_params=config_dict.get('validation_params', {}),
                    input_features=config_dict.get('input_features', []),
                    output_features=config_dict.get('output_features', []),
                    feature_preprocessing=config_dict.get('feature_preprocessing', {}),
                    min_accuracy=config_dict.get('min_accuracy', 0.7),
                    max_latency_ms=config_dict.get('max_latency_ms', 100.0),
                    auto_deploy=config_dict.get('auto_deploy', False),
                    a_b_test_enabled=config_dict.get('a_b_test_enabled', False),
                    canary_percentage=config_dict.get('canary_percentage', 10.0),
                    auto_retrain=config_dict.get('auto_retrain', True),
                    retrain_threshold=config_dict.get('retrain_threshold', 0.05),
                    retrain_interval_hours=config_dict.get('retrain_interval_hours', 24),
                    max_memory_mb=config_dict.get('max_memory_mb', 1024),
                    max_cpu_cores=config_dict.get('max_cpu_cores', 2)
                )
                
                self._model_configs[model_id] = config
                
                # Load metadata if exists
                metadata_file = self.models_directory / f"{model_id}_metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata_dict = json.load(f)
                    
                    metadata = ModelMetadata(config=config)
                    metadata.training_start_time = metadata_dict.get('training_start_time', 0.0)
                    metadata.training_end_time = metadata_dict.get('training_end_time', 0.0)
                    metadata.training_duration_seconds = metadata_dict.get('training_duration_seconds', 0.0)
                    metadata.training_samples = metadata_dict.get('training_samples', 0)
                    metadata.accuracy = metadata_dict.get('accuracy', 0.0)
                    metadata.precision = metadata_dict.get('precision', 0.0)
                    metadata.recall = metadata_dict.get('recall', 0.0)
                    metadata.f1_score = metadata_dict.get('f1_score', 0.0)
                    metadata.auc_score = metadata_dict.get('auc_score', 0.0)
                    metadata.custom_metrics = metadata_dict.get('custom_metrics', {})
                    metadata.model_path = metadata_dict.get('model_path', '')
                    metadata.model_size_bytes = metadata_dict.get('model_size_bytes', 0)
                    metadata.model_hash = metadata_dict.get('model_hash', '')
                    metadata.status = ModelStatus(metadata_dict.get('status', 'trained'))
                    metadata.deployment_time = metadata_dict.get('deployment_time', 0.0)
                    metadata.last_prediction_time = metadata_dict.get('last_prediction_time', 0.0)
                    metadata.prediction_count = metadata_dict.get('prediction_count', 0)
                    metadata.recent_accuracy = metadata_dict.get('recent_accuracy', 0.0)
                    metadata.performance_history = metadata_dict.get('performance_history', [])
                    
                    self._models[model_id] = metadata
                else:
                    # Create default metadata
                    self._models[model_id] = ModelMetadata(config=config)
                
                self.logger.info(f"Loaded model: {model_id}")
        
        except Exception as e:
            self.logger.error(f"Error loading existing models: {e}")
    
    async def _deploy_ab_test(self, model_id: str, model: ModelInterface, percentage: float):
        """Deploy model as A/B test"""
        # Simplified A/B test implementation
        self._ab_tests[model_id] = {
            'model': model,
            'percentage': percentage,
            'requests': 0,
            'successes': 0
        }
    
    async def _predict_ab_test(self, model_id: str, input_data: Any) -> Dict[str, Any]:
        """Make prediction using A/B test model"""
        import random
        
        ab_test = self._ab_tests[model_id]
        ab_test['requests'] += 1
        
        # Decide whether to use A/B test model based on percentage
        if random.random() * 100 < ab_test['percentage']:
            try:
                result = await self.predict(model_id, input_data)
                ab_test['successes'] += 1
                result['ab_test'] = True
                return result
            except Exception as e:
                self.logger.error(f"A/B test prediction failed for {model_id}: {e}")
                # Fallback to production model if available
                raise
        else:
            # Use production model (simplified - would need production model logic)
            raise ValueError("Production model not available for A/B test fallback")
    
    async def _monitoring_worker(self):
        """Background worker for model performance monitoring"""
        while self._running:
            try:
                await self._check_model_performance()
                await asyncio.sleep(300)  # Check every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Monitoring worker error: {e}")
                await asyncio.sleep(60)
    
    async def _retraining_worker(self):
        """Background worker for automated model retraining"""
        while self._running:
            try:
                await self._check_retraining_needs()
                await asyncio.sleep(3600)  # Check every hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Retraining worker error: {e}")
                await asyncio.sleep(300)
    
    async def _check_model_performance(self):
        """Check performance of deployed models"""
        # Simplified performance checking
        for model_id, metadata in self._models.items():
            if metadata.status == ModelStatus.DEPLOYED:
                # In practice, this would analyze recent predictions vs actual outcomes
                # For now, just log that monitoring is active
                self.logger.debug(f"Monitoring model {model_id} performance")
    
    async def _check_retraining_needs(self):
        """Check if any models need retraining"""
        current_time = time.time()
        
        for model_id, metadata in self._models.items():
            config = self._model_configs[model_id]
            
            if not config.auto_retrain or metadata.status != ModelStatus.DEPLOYED:
                continue
            
            # Check if enough time has passed since last training
            hours_since_training = (current_time - metadata.training_end_time) / 3600
            
            if hours_since_training >= config.retrain_interval_hours:
                self.logger.info(f"Model {model_id} needs retraining (last trained {hours_since_training:.1f} hours ago)")
                # In practice, this would trigger retraining with new data