"""
Model Versioning System
Version control and lifecycle management for ML models
"""

import asyncio
import hashlib
import json
import os
import pickle
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
import logging


class ModelStatus(Enum):
    """Model status in lifecycle"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ModelType(Enum):
    """Types of ML models"""
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    CLUSTERING = "clustering"
    REINFORCEMENT_LEARNING = "reinforcement_learning"
    DEEP_LEARNING = "deep_learning"
    ENSEMBLE = "ensemble"
    TIME_SERIES = "time_series"


@dataclass
class ModelMetadata:
    """Model metadata"""
    model_id: str
    version: str
    name: str
    description: str
    model_type: ModelType
    framework: str  # 'tensorflow', 'pytorch', 'sklearn', etc.
    created_at: datetime
    created_by: str
    tags: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    data_schema: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'model_id': self.model_id,
            'version': self.version,
            'name': self.name,
            'description': self.description,
            'model_type': self.model_type.value,
            'framework': self.framework,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'tags': self.tags,
            'parameters': self.parameters,
            'metrics': self.metrics,
            'dependencies': self.dependencies,
            'data_schema': self.data_schema
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelMetadata':
        """Create from dictionary"""
        return cls(
            model_id=data['model_id'],
            version=data['version'],
            name=data['name'],
            description=data['description'],
            model_type=ModelType(data['model_type']),
            framework=data['framework'],
            created_at=datetime.fromisoformat(data['created_at']),
            created_by=data['created_by'],
            tags=data.get('tags', []),
            parameters=data.get('parameters', {}),
            metrics=data.get('metrics', {}),
            dependencies=data.get('dependencies', []),
            data_schema=data.get('data_schema', {})
        )


@dataclass
class ModelVersion:
    """Model version information"""
    model_id: str
    version: str
    status: ModelStatus
    metadata: ModelMetadata
    model_path: str
    checksum: str
    size_bytes: int
    parent_version: Optional[str] = None
    deployment_config: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'model_id': self.model_id,
            'version': self.version,
            'status': self.status.value,
            'metadata': self.metadata.to_dict(),
            'model_path': self.model_path,
            'checksum': self.checksum,
            'size_bytes': self.size_bytes,
            'parent_version': self.parent_version,
            'deployment_config': self.deployment_config,
            'performance_metrics': self.performance_metrics
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelVersion':
        """Create from dictionary"""
        return cls(
            model_id=data['model_id'],
            version=data['version'],
            status=ModelStatus(data['status']),
            metadata=ModelMetadata.from_dict(data['metadata']),
            model_path=data['model_path'],
            checksum=data['checksum'],
            size_bytes=data['size_bytes'],
            parent_version=data.get('parent_version'),
            deployment_config=data.get('deployment_config', {}),
            performance_metrics=data.get('performance_metrics', {})
        )


class ModelVersioningSystem:
    """
    Model Versioning and Lifecycle Management System
    
    Features:
    - Semantic versioning (major.minor.patch)
    - Model artifact storage and retrieval
    - Metadata management
    - Status lifecycle management
    - Model comparison and diff
    - Rollback capabilities
    - Performance tracking
    """
    
    def __init__(self, storage_path: str = "./model_registry"):
        self.storage_path = Path(storage_path)
        self.logger = logging.getLogger(__name__)
        
        # Model registry
        self._models: Dict[str, Dict[str, ModelVersion]] = {}  # model_id -> version -> ModelVersion
        self._model_status: Dict[str, Dict[str, ModelStatus]] = {}  # model_id -> version -> status
        
        # Current production models
        self._production_models: Dict[str, str] = {}  # model_id -> version
        
        # Storage paths
        self.models_path = self.storage_path / "models"
        self.metadata_path = self.storage_path / "metadata"
        self.registry_file = self.storage_path / "registry.json"
        
        # Create directories
        self._create_directories()
        
        # Load existing registry
        self._load_registry()
    
    def _create_directories(self):
        """Create necessary directories"""
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.models_path.mkdir(parents=True, exist_ok=True)
        self.metadata_path.mkdir(parents=True, exist_ok=True)
    
    def _load_registry(self):
        """Load model registry from disk"""
        try:
            if self.registry_file.exists():
                with open(self.registry_file, 'r') as f:
                    registry_data = json.load(f)
                
                # Load models
                for model_id, versions in registry_data.get('models', {}).items():
                    self._models[model_id] = {}
                    for version, version_data in versions.items():
                        self._models[model_id][version] = ModelVersion.from_dict(version_data)
                
                # Load status
                for model_id, versions in registry_data.get('status', {}).items():
                    self._model_status[model_id] = {}
                    for version, status in versions.items():
                        self._model_status[model_id][version] = ModelStatus(status)
                
                # Load production models
                self._production_models = registry_data.get('production_models', {})
                
                self.logger.info(f"Loaded {len(self._models)} models from registry")
        
        except Exception as e:
            self.logger.error(f"Failed to load registry: {e}")
    
    def _save_registry(self):
        """Save model registry to disk"""
        try:
            registry_data = {
                'models': {
                    model_id: {
                        version: model_version.to_dict()
                        for version, model_version in versions.items()
                    }
                    for model_id, versions in self._models.items()
                },
                'status': {
                    model_id: {
                        version: status.value
                        for version, status in versions.items()
                    }
                    for model_id, versions in self._model_status.items()
                },
                'production_models': self._production_models
            }
            
            with open(self.registry_file, 'w') as f:
                json.dump(registry_data, f, indent=2)
        
        except Exception as e:
            self.logger.error(f"Failed to save registry: {e}")
    
    async def register_model(self, 
                           model_id: str,
                           model_artifact: Any,
                           metadata: ModelMetadata,
                           version: Optional[str] = None) -> str:
        """Register a new model version"""
        try:
            # Generate version if not provided
            if version is None:
                version = self._generate_next_version(model_id)
            
            # Validate version format
            if not self._is_valid_version(version):
                raise ValueError(f"Invalid version format: {version}")
            
            # Check if version already exists
            if model_id in self._models and version in self._models[model_id]:
                raise ValueError(f"Model {model_id} version {version} already exists")
            
            # Create model directory
            model_dir = self.models_path / model_id / version
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # Save model artifact
            model_path = model_dir / "model.pkl"
            await self._save_model_artifact(model_artifact, model_path)
            
            # Calculate checksum
            checksum = await self._calculate_checksum(model_path)
            
            # Get file size
            size_bytes = model_path.stat().st_size
            
            # Create model version
            model_version = ModelVersion(
                model_id=model_id,
                version=version,
                status=ModelStatus.DEVELOPMENT,
                metadata=metadata,
                model_path=str(model_path),
                checksum=checksum,
                size_bytes=size_bytes
            )
            
            # Store in registry
            if model_id not in self._models:
                self._models[model_id] = {}
                self._model_status[model_id] = {}
            
            self._models[model_id][version] = model_version
            self._model_status[model_id][version] = ModelStatus.DEVELOPMENT
            
            # Save metadata
            metadata_file = self.metadata_path / f"{model_id}_{version}.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata.to_dict(), f, indent=2)
            
            # Save registry
            self._save_registry()
            
            self.logger.info(f"Registered model {model_id} version {version}")
            return version
        
        except Exception as e:
            self.logger.error(f"Failed to register model: {e}")
            raise
    
    async def get_model(self, model_id: str, version: Optional[str] = None) -> Optional[Any]:
        """Get model artifact"""
        try:
            # Use production version if not specified
            if version is None:
                version = self._production_models.get(model_id)
                if version is None:
                    raise ValueError(f"No production version for model {model_id}")
            
            # Check if model exists
            if model_id not in self._models or version not in self._models[model_id]:
                return None
            
            model_version = self._models[model_id][version]
            
            # Load model artifact
            model_artifact = await self._load_model_artifact(model_version.model_path)
            
            return model_artifact
        
        except Exception as e:
            self.logger.error(f"Failed to get model {model_id}:{version}: {e}")
            return None
    
    async def get_model_metadata(self, model_id: str, version: str) -> Optional[ModelMetadata]:
        """Get model metadata"""
        if model_id not in self._models or version not in self._models[model_id]:
            return None
        
        return self._models[model_id][version].metadata
    
    async def update_model_status(self, model_id: str, version: str, status: ModelStatus):
        """Update model status"""
        if model_id not in self._models or version not in self._models[model_id]:
            raise ValueError(f"Model {model_id}:{version} not found")
        
        old_status = self._model_status[model_id][version]
        self._model_status[model_id][version] = status
        self._models[model_id][version].status = status
        
        # Handle production deployment
        if status == ModelStatus.PRODUCTION:
            # Demote current production model
            current_prod = self._production_models.get(model_id)
            if current_prod and current_prod != version:
                await self.update_model_status(model_id, current_prod, ModelStatus.STAGING)
            
            # Set new production model
            self._production_models[model_id] = version
        
        elif old_status == ModelStatus.PRODUCTION and status != ModelStatus.PRODUCTION:
            # Remove from production
            if self._production_models.get(model_id) == version:
                del self._production_models[model_id]
        
        self._save_registry()
        
        self.logger.info(f"Updated model {model_id}:{version} status: {old_status.value} -> {status.value}")
    
    async def promote_model(self, model_id: str, version: str) -> bool:
        """Promote model to next stage"""
        if model_id not in self._models or version not in self._models[model_id]:
            return False
        
        current_status = self._model_status[model_id][version]
        
        # Define promotion path
        promotion_path = {
            ModelStatus.DEVELOPMENT: ModelStatus.TESTING,
            ModelStatus.TESTING: ModelStatus.STAGING,
            ModelStatus.STAGING: ModelStatus.PRODUCTION
        }
        
        if current_status in promotion_path:
            next_status = promotion_path[current_status]
            await self.update_model_status(model_id, version, next_status)
            return True
        
        return False
    
    async def rollback_model(self, model_id: str, target_version: Optional[str] = None) -> bool:
        """Rollback to previous model version"""
        try:
            if model_id not in self._production_models:
                raise ValueError(f"No production model for {model_id}")
            
            current_version = self._production_models[model_id]
            
            if target_version is None:
                # Find previous production version
                target_version = await self._find_previous_production_version(model_id, current_version)
                if target_version is None:
                    raise ValueError(f"No previous production version found for {model_id}")
            
            # Validate target version exists and is in staging
            if (model_id not in self._models or 
                target_version not in self._models[model_id] or
                self._model_status[model_id][target_version] not in [ModelStatus.STAGING, ModelStatus.PRODUCTION]):
                raise ValueError(f"Invalid rollback target: {model_id}:{target_version}")
            
            # Demote current production model
            await self.update_model_status(model_id, current_version, ModelStatus.STAGING)
            
            # Promote target version to production
            await self.update_model_status(model_id, target_version, ModelStatus.PRODUCTION)
            
            self.logger.info(f"Rolled back model {model_id} from {current_version} to {target_version}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to rollback model {model_id}: {e}")
            return False
    
    async def delete_model_version(self, model_id: str, version: str) -> bool:
        """Delete a model version"""
        try:
            if model_id not in self._models or version not in self._models[model_id]:
                return False
            
            # Cannot delete production models
            if self._model_status[model_id][version] == ModelStatus.PRODUCTION:
                raise ValueError("Cannot delete production model")
            
            model_version = self._models[model_id][version]
            
            # Delete model files
            model_path = Path(model_version.model_path)
            if model_path.exists():
                model_path.unlink()
            
            # Delete model directory if empty
            model_dir = model_path.parent
            if model_dir.exists() and not any(model_dir.iterdir()):
                model_dir.rmdir()
            
            # Delete metadata file
            metadata_file = self.metadata_path / f"{model_id}_{version}.json"
            if metadata_file.exists():
                metadata_file.unlink()
            
            # Remove from registry
            del self._models[model_id][version]
            del self._model_status[model_id][version]
            
            # Clean up empty model entry
            if not self._models[model_id]:
                del self._models[model_id]
                del self._model_status[model_id]
            
            self._save_registry()
            
            self.logger.info(f"Deleted model {model_id}:{version}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to delete model {model_id}:{version}: {e}")
            return False
    
    async def list_models(self, status_filter: Optional[ModelStatus] = None) -> List[Dict[str, Any]]:
        """List all models"""
        models = []
        
        for model_id, versions in self._models.items():
            for version, model_version in versions.items():
                if status_filter is None or model_version.status == status_filter:
                    models.append({
                        'model_id': model_id,
                        'version': version,
                        'status': model_version.status.value,
                        'name': model_version.metadata.name,
                        'model_type': model_version.metadata.model_type.value,
                        'framework': model_version.metadata.framework,
                        'created_at': model_version.metadata.created_at.isoformat(),
                        'size_bytes': model_version.size_bytes,
                        'is_production': self._production_models.get(model_id) == version
                    })
        
        return sorted(models, key=lambda x: (x['model_id'], x['version']))
    
    async def list_model_versions(self, model_id: str) -> List[Dict[str, Any]]:
        """List versions of a specific model"""
        if model_id not in self._models:
            return []
        
        versions = []
        for version, model_version in self._models[model_id].items():
            versions.append({
                'version': version,
                'status': model_version.status.value,
                'created_at': model_version.metadata.created_at.isoformat(),
                'size_bytes': model_version.size_bytes,
                'checksum': model_version.checksum,
                'is_production': self._production_models.get(model_id) == version,
                'parent_version': model_version.parent_version,
                'metrics': model_version.performance_metrics
            })
        
        return sorted(versions, key=lambda x: self._version_sort_key(x['version']), reverse=True)
    
    async def compare_models(self, model_id: str, version1: str, version2: str) -> Dict[str, Any]:
        """Compare two model versions"""
        if (model_id not in self._models or 
            version1 not in self._models[model_id] or 
            version2 not in self._models[model_id]):
            raise ValueError("One or both model versions not found")
        
        mv1 = self._models[model_id][version1]
        mv2 = self._models[model_id][version2]
        
        comparison = {
            'model_id': model_id,
            'version1': version1,
            'version2': version2,
            'metadata_diff': self._compare_metadata(mv1.metadata, mv2.metadata),
            'performance_diff': self._compare_metrics(mv1.performance_metrics, mv2.performance_metrics),
            'size_diff': mv2.size_bytes - mv1.size_bytes,
            'status_diff': {
                'version1': mv1.status.value,
                'version2': mv2.status.value
            }
        }
        
        return comparison
    
    async def get_model_lineage(self, model_id: str, version: str) -> List[Dict[str, Any]]:
        """Get model version lineage"""
        if model_id not in self._models or version not in self._models[model_id]:
            return []
        
        lineage = []
        current_version = version
        
        while current_version:
            if current_version in self._models[model_id]:
                mv = self._models[model_id][current_version]
                lineage.append({
                    'version': current_version,
                    'status': mv.status.value,
                    'created_at': mv.metadata.created_at.isoformat(),
                    'created_by': mv.metadata.created_by,
                    'parent_version': mv.parent_version
                })
                current_version = mv.parent_version
            else:
                break
        
        return lineage
    
    def _generate_next_version(self, model_id: str) -> str:
        """Generate next semantic version"""
        if model_id not in self._models or not self._models[model_id]:
            return "1.0.0"
        
        # Get latest version
        versions = list(self._models[model_id].keys())
        versions.sort(key=self._version_sort_key, reverse=True)
        latest_version = versions[0]
        
        # Parse version
        parts = latest_version.split('.')
        if len(parts) != 3:
            return "1.0.0"
        
        try:
            major, minor, patch = map(int, parts)
            # Increment patch version
            return f"{major}.{minor}.{patch + 1}"
        except ValueError:
            return "1.0.0"
    
    def _is_valid_version(self, version: str) -> bool:
        """Validate semantic version format"""
        parts = version.split('.')
        if len(parts) != 3:
            return False
        
        try:
            major, minor, patch = map(int, parts)
            return major >= 0 and minor >= 0 and patch >= 0
        except ValueError:
            return False
    
    def _version_sort_key(self, version: str) -> Tuple[int, int, int]:
        """Generate sort key for version"""
        try:
            parts = version.split('.')
            return tuple(map(int, parts))
        except (ValueError, IndexError):
            return (0, 0, 0)
    
    async def _save_model_artifact(self, model_artifact: Any, model_path: Path):
        """Save model artifact to disk"""
        try:
            with open(model_path, 'wb') as f:
                pickle.dump(model_artifact, f)
        except Exception as e:
            self.logger.error(f"Failed to save model artifact: {e}")
            raise
    
    async def _load_model_artifact(self, model_path: str) -> Any:
        """Load model artifact from disk"""
        try:
            with open(model_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load model artifact: {e}")
            raise
    
    async def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate file checksum"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            self.logger.error(f"Failed to calculate checksum: {e}")
            return ""
    
    async def _find_previous_production_version(self, model_id: str, current_version: str) -> Optional[str]:
        """Find previous production version"""
        # This is a simplified implementation
        # In practice, you'd maintain a production history
        versions = list(self._models[model_id].keys())
        versions.sort(key=self._version_sort_key, reverse=True)
        
        current_index = versions.index(current_version)
        if current_index < len(versions) - 1:
            return versions[current_index + 1]
        
        return None
    
    def _compare_metadata(self, metadata1: ModelMetadata, metadata2: ModelMetadata) -> Dict[str, Any]:
        """Compare model metadata"""
        return {
            'name': {'v1': metadata1.name, 'v2': metadata2.name, 'changed': metadata1.name != metadata2.name},
            'description': {'v1': metadata1.description, 'v2': metadata2.description, 'changed': metadata1.description != metadata2.description},
            'model_type': {'v1': metadata1.model_type.value, 'v2': metadata2.model_type.value, 'changed': metadata1.model_type != metadata2.model_type},
            'framework': {'v1': metadata1.framework, 'v2': metadata2.framework, 'changed': metadata1.framework != metadata2.framework},
            'parameters': {'v1': metadata1.parameters, 'v2': metadata2.parameters, 'changed': metadata1.parameters != metadata2.parameters},
            'tags': {'v1': metadata1.tags, 'v2': metadata2.tags, 'changed': set(metadata1.tags) != set(metadata2.tags)}
        }
    
    def _compare_metrics(self, metrics1: Dict[str, float], metrics2: Dict[str, float]) -> Dict[str, Any]:
        """Compare performance metrics"""
        all_metrics = set(metrics1.keys()) | set(metrics2.keys())
        comparison = {}
        
        for metric in all_metrics:
            v1 = metrics1.get(metric)
            v2 = metrics2.get(metric)
            
            comparison[metric] = {
                'v1': v1,
                'v2': v2,
                'diff': (v2 - v1) if (v1 is not None and v2 is not None) else None,
                'pct_change': ((v2 - v1) / v1 * 100) if (v1 is not None and v2 is not None and v1 != 0) else None
            }
        
        return comparison
    
    def get_production_model(self, model_id: str) -> Optional[str]:
        """Get current production version"""
        return self._production_models.get(model_id)
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        total_models = len(self._models)
        total_versions = sum(len(versions) for versions in self._models.values())
        
        status_counts = {}
        for versions in self._model_status.values():
            for status in versions.values():
                status_counts[status.value] = status_counts.get(status.value, 0) + 1
        
        total_size = 0
        for versions in self._models.values():
            for model_version in versions.values():
                total_size += model_version.size_bytes
        
        return {
            'total_models': total_models,
            'total_versions': total_versions,
            'production_models': len(self._production_models),
            'status_distribution': status_counts,
            'total_size_bytes': total_size,
            'storage_path': str(self.storage_path)
        }