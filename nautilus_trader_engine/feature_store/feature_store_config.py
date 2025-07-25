"""
Feature Store Configuration for Feast

This module provides configuration for the Feast feature store integration,
including offline and online store configurations, feature definitions,
and data source configurations.

Features:
- Feast repository configuration
- Offline store (PostgreSQL/Parquet) configuration
- Online store (Redis) configuration
- Feature view definitions
- Data source configurations

Author: Vincent S. Pereira
Version: 1.0.0
"""

import os
from datetime import timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path

# Feast imports
try:
    from feast import (
        FeatureStore,
        Entity,
        FeatureView,
        Field,
        FileSource,
        PushSource,
        RequestSource,
        ValueType,
        FeatureService,
        OnDemandFeatureView,
        StreamFeatureView
    )
    from feast.types import Float32, Float64, Int32, Int64, String, Bool, UnixTimestamp
    from feast.infra.offline_stores.contrib.postgres_offline_store.postgres import (
        PostgreSQLOfflineStoreConfig
    )
    from feast.infra.online_stores.redis import RedisOnlineStoreConfig
    FEAST_AVAILABLE = True
except ImportError:
    print("Warning: Feast not available. Install with: pip install feast")
    FEAST_AVAILABLE = False


@dataclass
class FeatureStoreConfig:
    """Configuration for the feature store"""
    project_name: str = "nautilus_trading"
    registry_path: str = "feature_registry.db"
    
    # Offline store configuration
    offline_store_type: str = "file"  # "file", "postgres", "bigquery"
    offline_store_path: str = "data/offline_store"
    
    # Online store configuration
    online_store_type: str = "sqlite"  # "sqlite", "redis", "dynamodb"
    online_store_path: str = "data/online_store.db"
    
    # PostgreSQL configuration (if using postgres offline store)
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_database: str = os.getenv("POSTGRES_DATABASE", "nautilus_features")
    postgres_user: str = os.getenv("POSTGRES_USER", "postgres")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD")
    
    # Redis configuration (if using redis online store)
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    
    # Feature freshness settings
    default_ttl: timedelta = timedelta(days=1)
    max_age: timedelta = timedelta(days=7)
    
    @classmethod
    def from_env(cls) -> 'FeatureStoreConfig':
        """Create configuration from environment variables"""
        return cls(
            project_name=os.getenv("FEAST_PROJECT_NAME", "nautilus_trading"),
            registry_path=os.getenv("FEAST_REGISTRY_PATH", "feature_registry.db"),
            offline_store_type=os.getenv("FEAST_OFFLINE_STORE_TYPE", "file"),
            offline_store_path=os.getenv("FEAST_OFFLINE_STORE_PATH", "data/offline_store"),
            online_store_type=os.getenv("FEAST_ONLINE_STORE_TYPE", "sqlite"),
            online_store_path=os.getenv("FEAST_ONLINE_STORE_PATH", "data/online_store.db"),
            postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
            postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
            postgres_database=os.getenv("POSTGRES_DATABASE", "nautilus_features"),
            postgres_user=os.getenv("POSTGRES_USER", "postgres"),
            postgres_password=os.getenv("POSTGRES_PASSWORD", "password"),
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            redis_db=int(os.getenv("REDIS_DB", "0"))
        )
    
    def to_feast_config(self) -> Dict[str, Any]:
        """Convert to Feast configuration dictionary"""
        config = {
            "project": self.project_name,
            "registry": self.registry_path,
            "provider": "local",
        }
        
        # Configure offline store
        if self.offline_store_type == "file":
            config["offline_store"] = {
                "type": "file"
            }
        elif self.offline_store_type == "postgres":
            config["offline_store"] = {
                "type": "postgres",
                "host": self.postgres_host,
                "port": self.postgres_port,
                "database": self.postgres_database,
                "db_schema": "public",
                "user": self.postgres_user,
                "password": self.postgres_password
            }
        
        # Configure online store
        if self.online_store_type == "sqlite":
            config["online_store"] = {
                "type": "sqlite",
                "path": self.online_store_path
            }
        elif self.online_store_type == "redis":
            config["online_store"] = {
                "type": "redis",
                "connection_string": f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
            }
        
        return config
    
    def create_feast_repo_config(self, repo_path: str) -> str:
        """Create feature_store.yaml content for Feast repository"""
        config = self.to_feast_config()
        
        yaml_content = f"""# Feast Feature Store Configuration
project: {config['project']}
registry: {config['registry']}
provider: {config['provider']}

# Offline Store Configuration
offline_store:
"""
        
        if self.offline_store_type == "file":
            yaml_content += "    type: file\n"
        elif self.offline_store_type == "postgres":
            yaml_content += f"""    type: postgres
    host: {self.postgres_host}
    port: {self.postgres_port}
    database: {self.postgres_database}
    db_schema: public
    user: {self.postgres_user}
    password: {self.postgres_password}
"""
        
        yaml_content += "\n# Online Store Configuration\nonline_store:\n"
        
        if self.online_store_type == "sqlite":
            yaml_content += f"    type: sqlite\n    path: {self.online_store_path}\n"
        elif self.online_store_type == "redis":
            yaml_content += f"""    type: redis
    connection_string: redis://{self.redis_host}:{self.redis_port}/{self.redis_db}
"""
        
        yaml_content += f"""
# Entity Key Serialization Version
entity_key_serialization_version: 2

# Feature Server Configuration
feature_server:
    host: 0.0.0.0
    port: 6566
"""
        
        return yaml_content


class FeatureStoreManager:
    """Manager class for Feast feature store operations"""
    
    def __init__(self, config: FeatureStoreConfig, repo_path: str = "feature_repo"):
        self.config = config
        self.repo_path = Path(repo_path)
        self.store: Optional[FeatureStore] = None
        
    def initialize_repo(self) -> bool:
        """Initialize Feast repository"""
        if not FEAST_AVAILABLE:
            print("Error: Feast is not available")
            return False
        
        try:
            # Create repository directory
            self.repo_path.mkdir(exist_ok=True)
            
            # Create feature_store.yaml
            config_content = self.config.create_feast_repo_config(str(self.repo_path))
            config_file = self.repo_path / "feature_store.yaml"
            
            with open(config_file, 'w') as f:
                f.write(config_content)
            
            # Create data directories
            (self.repo_path / "data").mkdir(exist_ok=True)
            (self.repo_path / "data" / "offline_store").mkdir(exist_ok=True)
            
            print(f"✓ Feast repository initialized at {self.repo_path}")
            return True
            
        except Exception as e:
            print(f"✗ Error initializing Feast repository: {e}")
            return False
    
    def get_feature_store(self) -> Optional[FeatureStore]:
        """Get or create FeatureStore instance"""
        if not FEAST_AVAILABLE:
            return None
        
        if self.store is None:
            try:
                self.store = FeatureStore(repo_path=str(self.repo_path))
            except Exception as e:
                print(f"Error creating FeatureStore: {e}")
                return None
        
        return self.store
    
    def apply_features(self, feature_definitions: List[Any]) -> bool:
        """Apply feature definitions to the store"""
        store = self.get_feature_store()
        if not store:
            return False
        
        try:
            store.apply(feature_definitions)
            print(f"✓ Applied {len(feature_definitions)} feature definitions")
            return True
        except Exception as e:
            print(f"✗ Error applying features: {e}")
            return False
    
    def get_online_features(self, features: List[str], entity_rows: List[Dict[str, Any]]) -> Optional[Dict]:
        """Get features from online store"""
        store = self.get_feature_store()
        if not store:
            return None
        
        try:
            return store.get_online_features(
                features=features,
                entity_rows=entity_rows
            ).to_dict()
        except Exception as e:
            print(f"Error getting online features: {e}")
            return None
    
    def get_historical_features(self, entity_df, features: List[str]) -> Optional[Any]:
        """Get historical features from offline store"""
        store = self.get_feature_store()
        if not store:
            return None
        
        try:
            return store.get_historical_features(
                entity_df=entity_df,
                features=features
            )
        except Exception as e:
            print(f"Error getting historical features: {e}")
            return None
    
    def materialize_incremental(self, end_date) -> bool:
        """Materialize incremental features to online store"""
        store = self.get_feature_store()
        if not store:
            return False
        
        try:
            store.materialize_incremental(end_date=end_date)
            print("✓ Incremental materialization completed")
            return True
        except Exception as e:
            print(f"✗ Error in incremental materialization: {e}")
            return False
    
    def get_feature_service(self, name: str) -> Optional[Any]:
        """Get feature service by name"""
        store = self.get_feature_store()
        if not store:
            return None
        
        try:
            return store.get_feature_service(name)
        except Exception as e:
            print(f"Error getting feature service '{name}': {e}")
            return None


def create_feature_store_manager(config_path: Optional[str] = None) -> FeatureStoreManager:
    """Factory function to create feature store manager"""
    if config_path and os.path.exists(config_path):
        # Load from config file (would implement YAML/JSON loading)
        config = FeatureStoreConfig.from_env()
    else:
        config = FeatureStoreConfig.from_env()
    
    return FeatureStoreManager(config)


def test_feature_store_config():
    """Test feature store configuration"""
    print("Testing Feature Store Configuration...")
    print("=" * 50)
    
    # Create configuration
    config = FeatureStoreConfig.from_env()
    print(f"Project: {config.project_name}")
    print(f"Offline Store: {config.offline_store_type}")
    print(f"Online Store: {config.online_store_type}")
    
    # Create manager
    manager = create_feature_store_manager()
    
    # Test repository initialization
    if manager.initialize_repo():
        print("✓ Repository initialization test passed")
    else:
        print("✗ Repository initialization test failed")
    
    # Test YAML generation
    yaml_content = config.create_feast_repo_config("test_repo")
    print("\nGenerated feature_store.yaml:")
    print(yaml_content[:200] + "..." if len(yaml_content) > 200 else yaml_content)
    
    print("\nFeature store configuration test completed!")


if __name__ == "__main__":
    test_feature_store_config()