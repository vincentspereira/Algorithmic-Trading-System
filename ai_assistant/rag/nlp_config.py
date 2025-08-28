"""
NLP Configuration for AI Assistant - Phase 3
Centralized configuration management for NLP and explainability services

This module provides:
1. Configuration management for different NLP models
2. Model download and caching settings
3. Performance optimization parameters
4. Language and domain settings
5. Integration settings for various services
6. Environment-specific configurations

All NLP components use this centralized configuration system for
consistent behavior and easy customization.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelProvider(Enum):
    """Supported model providers"""
    HUGGINGFACE = "huggingface"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


class CacheStrategy(Enum):
    """Cache strategies for models and results"""
    MEMORY = "memory"
    DISK = "disk"
    REDIS = "redis"
    HYBRID = "hybrid"
    NONE = "none"


class OptimizationLevel(Enum):
    """Performance optimization levels"""
    SPEED = "speed"
    ACCURACY = "accuracy"
    BALANCED = "balanced"
    MEMORY = "memory"


@dataclass
class ModelConfig:
    """Configuration for individual models"""
    name: str
    provider: ModelProvider
    model_id: str
    enabled: bool = True
    cache_dir: str = "./models"
    max_length: int = 512
    batch_size: int = 16
    device: str = "auto"  # auto, cpu, cuda, mps
    precision: str = "fp32"  # fp32, fp16, int8
    optimization_level: OptimizationLevel = OptimizationLevel.BALANCED
    custom_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheConfig:
    """Configuration for caching"""
    strategy: CacheStrategy = CacheStrategy.MEMORY
    max_size: int = 1000
    ttl_hours: int = 24
    redis_url: Optional[str] = None
    disk_cache_dir: str = "./cache"
    compression: bool = True
    cleanup_interval_hours: int = 6


@dataclass
class PerformanceConfig:
    """Configuration for performance optimization"""
    max_workers: int = 4
    timeout_seconds: int = 30
    enable_gpu: bool = True
    enable_mixed_precision: bool = False
    enable_model_parallelism: bool = False
    memory_limit_gb: Optional[float] = None
    batch_processing: bool = True
    async_processing: bool = True


@dataclass
class SecurityConfig:
    """Configuration for security settings"""
    enable_input_validation: bool = True
    max_input_length: int = 10000
    allowed_file_types: List[str] = field(default_factory=lambda: ['.txt', '.md', '.json', '.csv'])
    sanitize_inputs: bool = True
    rate_limiting: bool = True
    max_requests_per_minute: int = 100


class NLPConfig:
    """
    Centralized configuration manager for NLP services
    """
    
    def __init__(self, config_path: Optional[str] = None, environment: str = "development"):
        """
        Initialize NLP configuration
        
        Args:
            config_path: Path to configuration file
            environment: Environment name (development, staging, production)
        """
        self.environment = environment
        self.config_path = config_path
        self._config = self._load_configuration()
        
        logger.info(f"NLP Configuration initialized for {environment} environment")
    
    def _load_configuration(self) -> Dict[str, Any]:
        """
        Load configuration from file or create default
        """
        # Start with default configuration
        config = self._get_default_config()
        
        # Load from file if provided
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    file_config = json.load(f)
                    config = self._merge_configs(config, file_config)
                logger.info(f"Configuration loaded from {self.config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config from {self.config_path}: {e}")
        
        # Load financial domain data from external JSON
        financial_data_path = Path(__file__).parent / "config" / "financial_nlp_data.json"
        if financial_data_path.exists():
            try:
                with open(financial_data_path, 'r') as f:
                    financial_data = json.load(f)
                    config["financial_domain"] = financial_data
                logger.info(f"Financial domain data loaded from {financial_data_path}")
            except Exception as e:
                logger.warning(f"Failed to load financial domain data from {financial_data_path}: {e}")
        else:
            logger.warning(f"Financial domain data file not found: {financial_data_path}")

        # Apply environment-specific overrides
        config = self._apply_environment_overrides(config)
        
        # Validate configuration
        self._validate_config(config)
        
        return config
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "models": {
                "finbert": {
                    "name": "finbert",
                    "provider": "huggingface",
                    "model_id": "ProsusAI/finbert",
                    "enabled": True,
                    "cache_dir": "./models/finbert",
                    "max_length": 512,
                    "batch_size": 16,
                    "device": "auto",
                    "precision": "fp32",
                    "optimization_level": "balanced"
                },
                "finbert_esg": {
                    "name": "finbert_esg",
                    "provider": "huggingface",
                    "model_id": "ProsusAI/finbert-esg",
                    "enabled": False,
                    "cache_dir": "./models/finbert_esg",
                    "max_length": 512,
                    "batch_size": 16,
                    "device": "auto",
                    "precision": "fp32",
                    "optimization_level": "balanced"
                },
                "roberta_sentiment": {
                    "name": "roberta_sentiment",
                    "provider": "huggingface",
                    "model_id": "cardiffnlp/twitter-roberta-base-sentiment-latest",
                    "enabled": True,
                    "cache_dir": "./models/roberta_sentiment",
                    "max_length": 512,
                    "batch_size": 16,
                    "device": "auto",
                    "precision": "fp32",
                    "optimization_level": "speed"
                },
                "bert_ner": {
                    "name": "bert_ner",
                    "provider": "huggingface",
                    "model_id": "dbmdz/bert-large-cased-finetuned-conll03-english",
                    "enabled": True,
                    "cache_dir": "./models/bert_ner",
                    "max_length": 512,
                    "batch_size": 8,
                    "device": "auto",
                    "precision": "fp32",
                    "optimization_level": "accuracy"
                },
                "t5_summarization": {
                    "name": "t5_summarization",
                    "provider": "huggingface",
                    "model_id": "t5-small",
                    "enabled": True,
                    "cache_dir": "./models/t5_summarization",
                    "max_length": 512,
                    "batch_size": 4,
                    "device": "auto",
                    "precision": "fp32",
                    "optimization_level": "balanced"
                },
                "roberta_qa": {
                    "name": "roberta_qa",
                    "provider": "huggingface",
                    "model_id": "deepset/roberta-base-squad2",
                    "enabled": True,
                    "cache_dir": "./models/roberta_qa",
                    "max_length": 512,
                    "batch_size": 8,
                    "device": "auto",
                    "precision": "fp32",
                    "optimization_level": "balanced"
                }
            },
            "cache": {
                "strategy": "memory",
                "max_size": 1000,
                "ttl_hours": 24,
                "redis_url": None,
                "disk_cache_dir": "./cache/nlp",
                "compression": True,
                "cleanup_interval_hours": 6
            },
            "performance": {
                "max_workers": 4,
                "timeout_seconds": 30,
                "enable_gpu": True,
                "enable_mixed_precision": False,
                "enable_model_parallelism": False,
                "memory_limit_gb": None,
                "batch_processing": True,
                "async_processing": True
            },
            "security": {
                "enable_input_validation": True,
                "max_input_length": 10000,
                "allowed_file_types": [".txt", ".md", ".json", ".csv", ".pdf", ".docx"],
                "sanitize_inputs": True,
                "rate_limiting": True,
                "max_requests_per_minute": 100
            },
            "explainability": {
                "shap": {
                    "enabled": True,
                    "kernel_explainer": {
                        "n_samples": 100,
                        "l1_reg": "auto"
                    },
                    "tree_explainer": {
                        "feature_perturbation": "tree_path_dependent",
                        "check_additivity": False
                    },
                    "linear_explainer": {
                        "feature_perturbation": "correlation_dependent"
                    }
                },
                "visualization": {
                    "max_display": 20,
                    "plot_size": [12, 8],
                    "color_scheme": "RdYlBu",
                    "export_format": "html",
                    "interactive": True
                },
                "counterfactuals": {
                    "max_iterations": 100,
                    "tolerance": 0.01,
                    "feature_ranges": {}
                }
            },
            "financial_domain": {},
            "integration": {
                "rag_pipeline": {
                    "enabled": True,
                    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                    "vector_store": "qdrant",
                    "chunk_size": 512,
                    "chunk_overlap": 50
                },
                "forecasting_models": {
                    "enabled": True,
                    "feature_store": "feast",
                    "model_registry": "mlflow"
                },
                "tools_integration": {
                    "enabled": True,
                    "langchain_tools": True,
                    "react_agent": True
                }
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": "./logs/nlp.log",
                "max_file_size": "10MB",
                "backup_count": 5,
                "enable_structured_logging": True
            }
        }
    
    def _merge_configs(self, base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge configuration dictionaries"""
        merged = base_config.copy()
        
        for key, value in override_config.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value
        
        return merged
    
    def _apply_environment_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment-specific configuration overrides"""
        if self.environment == "production":
            # Production optimizations
            config["performance"]["enable_mixed_precision"] = True
            config["cache"]["strategy"] = "redis"
            config["cache"]["ttl_hours"] = 48
            config["security"]["rate_limiting"] = True
            config["logging"]["level"] = "WARNING"
            
        elif self.environment == "development":
            # Development settings
            config["performance"]["enable_gpu"] = False
            config["cache"]["strategy"] = "memory"
            config["cache"]["max_size"] = 100
            config["security"]["rate_limiting"] = False
            config["logging"]["level"] = "DEBUG"
            
        elif self.environment == "testing":
            # Testing settings
            config["performance"]["enable_gpu"] = False
            config["cache"]["strategy"] = "none"
            config["security"]["rate_limiting"] = False
            config["logging"]["level"] = "ERROR"
            
            # Disable some models for faster testing
            for model_name in ["finbert_esg", "t5_summarization"]:
                if model_name in config["models"]:
                    config["models"][model_name]["enabled"] = False
        
        # Apply environment variables
        config = self._apply_env_vars(config)
        
        return config
    
    def _apply_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides"""
        env_mappings = {
            "NLP_CACHE_STRATEGY": ("cache", "strategy"),
            "NLP_CACHE_TTL_HOURS": ("cache", "ttl_hours"),
            "NLP_MAX_WORKERS": ("performance", "max_workers"),
            "NLP_ENABLE_GPU": ("performance", "enable_gpu"),
            "NLP_TIMEOUT_SECONDS": ("performance", "timeout_seconds"),
            "NLP_LOG_LEVEL": ("logging", "level"),
            "REDIS_URL": ("cache", "redis_url"),
            "NLP_MEMORY_LIMIT_GB": ("performance", "memory_limit_gb"),
            "NLP_MAX_INPUT_LENGTH": ("security", "max_input_length")
        }
        
        for env_var, (section, key) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Type conversion
                if key in ["ttl_hours", "max_workers", "timeout_seconds", "max_input_length"]:
                    value = int(value)
                elif key in ["enable_gpu"]:
                    value = value.lower() in ["true", "1", "yes"]
                elif key in ["memory_limit_gb"]:
                    value = float(value) if value else None
                
                config[section][key] = value
        
        return config
    
    def _validate_config(self, config: Dict[str, Any]):
        """Validate configuration values"""
        # Validate model configurations
        for model_name, model_config in config["models"].items():
            if model_config["enabled"]:
                if not model_config.get("model_id"):
                    raise ValueError(f"Model {model_name} is enabled but has no model_id")
                
                if model_config["batch_size"] <= 0:
                    raise ValueError(f"Model {model_name} has invalid batch_size")
                
                if model_config["max_length"] <= 0:
                    raise ValueError(f"Model {model_name} has invalid max_length")
        
        # Validate cache configuration
        cache_config = config["cache"]
        if cache_config["strategy"] == "redis" and not cache_config.get("redis_url"):
            logger.warning("Redis cache strategy selected but no redis_url provided")
        
        # Validate performance configuration
        perf_config = config["performance"]
        if perf_config["max_workers"] <= 0:
            raise ValueError("max_workers must be positive")
        
        if perf_config["timeout_seconds"] <= 0:
            raise ValueError("timeout_seconds must be positive")
        
        # Validate security configuration
        security_config = config["security"]
        if security_config["max_input_length"] <= 0:
            raise ValueError("max_input_length must be positive")
    
    def get_model_config(self, model_name: str) -> ModelConfig:
        """Get configuration for a specific model"""
        if model_name not in self._config["models"]:
            raise ValueError(f"Model {model_name} not found in configuration")
        
        model_data = self._config["models"][model_name]
        
        return ModelConfig(
            name=model_data["name"],
            provider=ModelProvider(model_data["provider"]),
            model_id=model_data["model_id"],
            enabled=model_data["enabled"],
            cache_dir=model_data["cache_dir"],
            max_length=model_data["max_length"],
            batch_size=model_data["batch_size"],
            device=model_data["device"],
            precision=model_data["precision"],
            optimization_level=OptimizationLevel(model_data["optimization_level"]),
            custom_params=model_data.get("custom_params", {})
        )
    
    def get_cache_config(self) -> CacheConfig:
        """Get cache configuration"""
        cache_data = self._config["cache"]
        
        return CacheConfig(
            strategy=CacheStrategy(cache_data["strategy"]),
            max_size=cache_data["max_size"],
            ttl_hours=cache_data["ttl_hours"],
            redis_url=cache_data.get("redis_url"),
            disk_cache_dir=cache_data["disk_cache_dir"],
            compression=cache_data["compression"],
            cleanup_interval_hours=cache_data["cleanup_interval_hours"]
        )
    
    def get_performance_config(self) -> PerformanceConfig:
        """Get performance configuration"""
        perf_data = self._config["performance"]
        
        return PerformanceConfig(
            max_workers=perf_data["max_workers"],
            timeout_seconds=perf_data["timeout_seconds"],
            enable_gpu=perf_data["enable_gpu"],
            enable_mixed_precision=perf_data["enable_mixed_precision"],
            enable_model_parallelism=perf_data["enable_model_parallelism"],
            memory_limit_gb=perf_data.get("memory_limit_gb"),
            batch_processing=perf_data["batch_processing"],
            async_processing=perf_data["async_processing"]
        )
    
    def get_security_config(self) -> SecurityConfig:
        """Get security configuration"""
        security_data = self._config["security"]
        
        return SecurityConfig(
            enable_input_validation=security_data["enable_input_validation"],
            max_input_length=security_data["max_input_length"],
            allowed_file_types=security_data["allowed_file_types"],
            sanitize_inputs=security_data["sanitize_inputs"],
            rate_limiting=security_data["rate_limiting"],
            max_requests_per_minute=security_data["max_requests_per_minute"]
        )
    
    def get_enabled_models(self) -> List[str]:
        """Get list of enabled model names"""
        return [
            name for name, config in self._config["models"].items()
            if config["enabled"]
        ]
    
    def get_financial_domain_config(self) -> Dict[str, Any]:
        """Get financial domain configuration"""
        return self._config["financial_domain"]
    
    def get_explainability_config(self) -> Dict[str, Any]:
        """Get explainability configuration"""
        return self._config["explainability"]
    
    def get_integration_config(self) -> Dict[str, Any]:
        """Get integration configuration"""
        return self._config["integration"]
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return self._config["logging"]
    
    def update_model_config(self, model_name: str, updates: Dict[str, Any]):
        """Update configuration for a specific model"""
        if model_name not in self._config["models"]:
            raise ValueError(f"Model {model_name} not found in configuration")
        
        self._config["models"][model_name].update(updates)
        logger.info(f"Updated configuration for model {model_name}")
    
    def enable_model(self, model_name: str):
        """Enable a specific model"""
        self.update_model_config(model_name, {"enabled": True})
    
    def disable_model(self, model_name: str):
        """Disable a specific model"""
        self.update_model_config(model_name, {"enabled": False})
    
    def save_config(self, output_path: str):
        """Save current configuration to file"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(self._config, f, indent=2)
            
            logger.info(f"Configuration saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of the current configuration"""
        enabled_models = self.get_enabled_models()
        
        return {
            "environment": self.environment,
            "config_path": self.config_path,
            "enabled_models": enabled_models,
            "total_models": len(self._config["models"]),
            "cache_strategy": self._config["cache"]["strategy"],
            "performance_settings": {
                "max_workers": self._config["performance"]["max_workers"],
                "enable_gpu": self._config["performance"]["enable_gpu"],
                "batch_processing": self._config["performance"]["batch_processing"]
            },
            "security_enabled": self._config["security"]["enable_input_validation"],
            "explainability_enabled": self._config["explainability"]["shap"]["enabled"],
            "integrations": {
                "rag_pipeline": self._config["integration"]["rag_pipeline"]["enabled"],
                "forecasting_models": self._config["integration"]["forecasting_models"]["enabled"],
                "tools_integration": self._config["integration"]["tools_integration"]["enabled"]
            }
        }


# Global configuration instance
_global_config: Optional[NLPConfig] = None


def get_config(config_path: Optional[str] = None, environment: str = None) -> NLPConfig:
    """
    Get global NLP configuration instance
    
    Args:
        config_path: Path to configuration file
        environment: Environment name
        
    Returns:
        NLPConfig instance
    """
    global _global_config
    
    if _global_config is None:
        if environment is None:
            environment = os.getenv("NLP_ENVIRONMENT", "development")
        
        _global_config = NLPConfig(config_path, environment)
    
    return _global_config


def reset_config():
    """Reset global configuration (useful for testing)"""
    global _global_config
    _global_config = None


# Convenience functions
def get_model_config(model_name: str) -> ModelConfig:
    """Get model configuration"""
    return get_config().get_model_config(model_name)


def get_enabled_models() -> List[str]:
    """Get list of enabled models"""
    return get_config().get_enabled_models()


def get_financial_terms() -> List[str]:
    """Get list of financial terms"""
    return get_config().get_financial_domain_config()["financial_terms"]


def get_cache_config() -> CacheConfig:
    """Get cache configuration"""
    return get_config().get_cache_config()


def get_performance_config() -> PerformanceConfig:
    """Get performance configuration"""
    return get_config().get_performance_config()


# Export main classes and functions
__all__ = [
    "NLPConfig",
    "ModelConfig",
    "CacheConfig", 
    "PerformanceConfig",
    "SecurityConfig",
    "ModelProvider",
    "CacheStrategy",
    "OptimizationLevel",
    "get_config",
    "reset_config",
    "get_model_config",
    "get_enabled_models",
    "get_financial_terms",
    "get_cache_config",
    "get_performance_config"
]