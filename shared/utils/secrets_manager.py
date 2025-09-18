"""Secrets Management Service

Provides secure storage and retrieval of sensitive configuration data
including API keys, database credentials, and certificates.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

try:
    import hvac  # HashiCorp Vault client
except ImportError:
    hvac = None

try:
    import boto3  # AWS SDK
except ImportError:
    boto3 = None

try:
    from azure.keyvault.secrets import SecretClient
    from azure.identity import DefaultAzureCredential
except ImportError:
    SecretClient = None
    DefaultAzureCredential = None

from ..config import settings
from config.encryption_config import encryption_manager, encryption_settings

logger = logging.getLogger(__name__)

class SecretsBackend(ABC):
    """Abstract base class for secrets backends"""
    
    @abstractmethod
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret by key"""
        pass
    
    @abstractmethod
    def set_secret(self, key: str, value: str) -> bool:
        """Store a secret"""
        pass
    
    @abstractmethod
    def delete_secret(self, key: str) -> bool:
        """Delete a secret"""
        pass
    
    @abstractmethod
    def list_secrets(self) -> list:
        """List all secret keys"""
        pass

class FileSecretsBackend(SecretsBackend):
    """File-based secrets backend with encryption"""
    
    def __init__(self, secrets_path: str):
        self.secrets_path = Path(secrets_path)
        self.secrets_file = self.secrets_path / "secrets.json"
        self.secrets_path.mkdir(parents=True, exist_ok=True)
        
        # Set restrictive permissions on secrets directory
        os.chmod(self.secrets_path, 0o700)
    
    def _load_secrets(self) -> Dict[str, Any]:
        """Load and decrypt secrets from file"""
        if not self.secrets_file.exists():
            return {}
        
        try:
            with open(self.secrets_file, 'rb') as f:
                encrypted_data = f.read()
            
            if encryption_settings.SECRETS_ENCRYPTION_ENABLED:
                decrypted_data = encryption_manager.decrypt_data(encrypted_data)
                return json.loads(decrypted_data.decode('utf-8'))
            else:
                return json.loads(encrypted_data.decode('utf-8'))
        except Exception as e:
            logger.error(f"Failed to load secrets: {e}")
            return {}
    
    def _save_secrets(self, secrets: Dict[str, Any]) -> bool:
        """Encrypt and save secrets to file"""
        try:
            data = json.dumps(secrets, indent=2).encode('utf-8')
            
            if encryption_settings.SECRETS_ENCRYPTION_ENABLED:
                encrypted_data = encryption_manager.encrypt_data(data)
            else:
                encrypted_data = data
            
            with open(self.secrets_file, 'wb') as f:
                f.write(encrypted_data)
            
            # Set restrictive permissions
            os.chmod(self.secrets_file, 0o600)
            return True
        except Exception as e:
            logger.error(f"Failed to save secrets: {e}")
            return False
    
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret by key"""
        secrets = self._load_secrets()
        secret_data = secrets.get(key)
        
        if secret_data:
            # Check if secret has expiration
            if isinstance(secret_data, dict):
                expires_at = secret_data.get('expires_at')
                if expires_at and datetime.fromisoformat(expires_at) < datetime.now():
                    logger.warning(f"Secret '{key}' has expired")
                    return None
                return secret_data.get('value')
            return secret_data
        
        return None
    
    def set_secret(self, key: str, value: str, expires_in_days: Optional[int] = None) -> bool:
        """Store a secret with optional expiration"""
        secrets = self._load_secrets()
        
        secret_data = {
            'value': value,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        if expires_in_days:
            expires_at = datetime.now() + timedelta(days=expires_in_days)
            secret_data['expires_at'] = expires_at.isoformat()
        
        secrets[key] = secret_data
        return self._save_secrets(secrets)
    
    def delete_secret(self, key: str) -> bool:
        """Delete a secret"""
        secrets = self._load_secrets()
        if key in secrets:
            del secrets[key]
            return self._save_secrets(secrets)
        return False
    
    def list_secrets(self) -> list:
        """List all secret keys"""
        secrets = self._load_secrets()
        return list(secrets.keys())

class VaultSecretsBackend(SecretsBackend):
    """HashiCorp Vault secrets backend"""
    
    def __init__(self, vault_url: str, vault_token: str, mount_point: str = "secret"):
        if hvac is None:
            raise ImportError("hvac library required for Vault backend")
        
        self.client = hvac.Client(url=vault_url, token=vault_token)
        self.mount_point = mount_point
        
        if not self.client.is_authenticated():
            raise ValueError("Failed to authenticate with Vault")
    
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret from Vault"""
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=key, mount_point=self.mount_point
            )
            return response['data']['data'].get('value')
        except Exception as e:
            logger.error(f"Failed to retrieve secret from Vault: {e}")
            return None
    
    def set_secret(self, key: str, value: str) -> bool:
        """Store a secret in Vault"""
        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                path=key,
                secret={'value': value},
                mount_point=self.mount_point
            )
            return True
        except Exception as e:
            logger.error(f"Failed to store secret in Vault: {e}")
            return False
    
    def delete_secret(self, key: str) -> bool:
        """Delete a secret from Vault"""
        try:
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=key, mount_point=self.mount_point
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret from Vault: {e}")
            return False
    
    def list_secrets(self) -> list:
        """List all secret keys in Vault"""
        try:
            response = self.client.secrets.kv.v2.list_secrets(
                path='', mount_point=self.mount_point
            )
            return response['data']['keys']
        except Exception as e:
            logger.error(f"Failed to list secrets from Vault: {e}")
            return []

class AWSSecretsBackend(SecretsBackend):
    """AWS Secrets Manager backend"""
    
    def __init__(self, region: str, access_key_id: str = None, secret_access_key: str = None):
        if boto3 is None:
            raise ImportError("boto3 library required for AWS Secrets Manager backend")
        
        session = boto3.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region
        )
        self.client = session.client('secretsmanager')
    
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret from AWS Secrets Manager"""
        try:
            response = self.client.get_secret_value(SecretId=key)
            return response['SecretString']
        except Exception as e:
            logger.error(f"Failed to retrieve secret from AWS: {e}")
            return None
    
    def set_secret(self, key: str, value: str) -> bool:
        """Store a secret in AWS Secrets Manager"""
        try:
            self.client.create_secret(Name=key, SecretString=value)
            return True
        except self.client.exceptions.ResourceExistsException:
            # Update existing secret
            try:
                self.client.update_secret(SecretId=key, SecretString=value)
                return True
            except Exception as e:
                logger.error(f"Failed to update secret in AWS: {e}")
                return False
        except Exception as e:
            logger.error(f"Failed to store secret in AWS: {e}")
            return False
    
    def delete_secret(self, key: str) -> bool:
        """Delete a secret from AWS Secrets Manager"""
        try:
            self.client.delete_secret(SecretId=key, ForceDeleteWithoutRecovery=True)
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret from AWS: {e}")
            return False
    
    def list_secrets(self) -> list:
        """List all secret keys in AWS Secrets Manager"""
        try:
            response = self.client.list_secrets()
            return [secret['Name'] for secret in response['SecretList']]
        except Exception as e:
            logger.error(f"Failed to list secrets from AWS: {e}")
            return []

class AzureSecretsBackend(SecretsBackend):
    """Azure Key Vault secrets backend"""
    
    def __init__(self, vault_url: str):
        if SecretClient is None or DefaultAzureCredential is None:
            raise ImportError("azure-keyvault-secrets library required for Azure backend")
        
        credential = DefaultAzureCredential()
        self.client = SecretClient(vault_url=vault_url, credential=credential)
    
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret from Azure Key Vault"""
        try:
            secret = self.client.get_secret(key)
            return secret.value
        except Exception as e:
            logger.error(f"Failed to retrieve secret from Azure: {e}")
            return None
    
    def set_secret(self, key: str, value: str) -> bool:
        """Store a secret in Azure Key Vault"""
        try:
            self.client.set_secret(key, value)
            return True
        except Exception as e:
            logger.error(f"Failed to store secret in Azure: {e}")
            return False
    
    def delete_secret(self, key: str) -> bool:
        """Delete a secret from Azure Key Vault"""
        try:
            self.client.begin_delete_secret(key)
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret from Azure: {e}")
            return False
    
    def list_secrets(self) -> list:
        """List all secret keys in Azure Key Vault"""
        try:
            secrets = self.client.list_properties_of_secrets()
            return [secret.name for secret in secrets]
        except Exception as e:
            logger.error(f"Failed to list secrets from Azure: {e}")
            return []

class SecretsManager:
    """Main secrets manager that handles different backends"""
    
    def __init__(self):
        self.backend = self._initialize_backend()
    
    def _initialize_backend(self) -> SecretsBackend:
        """Initialize the appropriate secrets backend"""
        backend_type = encryption_settings.SECRETS_BACKEND.lower()
        
        if backend_type == "file":
            return FileSecretsBackend(encryption_settings.SECRETS_PATH)
        
        elif backend_type == "vault":
            if hvac is None:
                logger.warning("Vault backend requested but hvac not installed, falling back to file backend")
                return FileSecretsBackend(encryption_settings.SECRETS_PATH)
            
            return VaultSecretsBackend(
                vault_url=encryption_settings.VAULT_URL,
                vault_token=encryption_settings.VAULT_TOKEN,
                mount_point=encryption_settings.VAULT_MOUNT_POINT
            )
        
        elif backend_type == "aws_secrets":
            if boto3 is None:
                logger.warning("AWS backend requested but boto3 not installed, falling back to file backend")
                return FileSecretsBackend(encryption_settings.SECRETS_PATH)
            
            return AWSSecretsBackend(
                region=encryption_settings.AWS_SECRETS_REGION,
                access_key_id=encryption_settings.AWS_ACCESS_KEY_ID,
                secret_access_key=encryption_settings.AWS_SECRET_ACCESS_KEY
            )
        
        elif backend_type == "azure_keyvault":
            if SecretClient is None:
                logger.warning("Azure backend requested but azure-keyvault-secrets not installed, falling back to file backend")
                return FileSecretsBackend(encryption_settings.SECRETS_PATH)
            
            return AzureSecretsBackend(encryption_settings.AZURE_VAULT_URL)
        
        else:
            logger.warning(f"Unknown backend type '{backend_type}', falling back to file backend")
            return FileSecretsBackend(encryption_settings.SECRETS_PATH)
    
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a secret value"""
        # First try environment variable
        env_value = os.getenv(key)
        if env_value:
            return env_value
        
        # Then try secrets backend
        value = self.backend.get_secret(key)
        return value if value is not None else default
    
    def set_secret(self, key: str, value: str, **kwargs) -> bool:
        """Set a secret value"""
        return self.backend.set_secret(key, value, **kwargs)
    
    def delete_secret(self, key: str) -> bool:
        """Delete a secret"""
        return self.backend.delete_secret(key)
    
    def list_secrets(self) -> list:
        """List all secret keys"""
        return self.backend.list_secrets()
    
    def get_database_credentials(self) -> Dict[str, str]:
        """Get database connection credentials"""
        return {
            'host': self.get_secret('DB_HOST', 'localhost'),
            'port': self.get_secret('DB_PORT', '5432'),
            'database': self.get_secret('DB_NAME', 'trading_db'),
            'username': self.get_secret('DB_USER', 'postgres'),
            'password': self.get_secret('DB_PASSWORD', ''),
        }
    
    def get_api_keys(self) -> Dict[str, str]:
        """Get API keys for external services"""
        return {
            'openai': self.get_secret('OPENAI_API_KEY', ''),
            'alpha_vantage': self.get_secret('ALPHA_VANTAGE_API_KEY', ''),
            'finnhub': self.get_secret('FINNHUB_API_KEY', ''),
            'polygon': self.get_secret('POLYGON_API_KEY', ''),
            'twelve_data': self.get_secret('TWELVE_DATA_API_KEY', ''),
        }
    
    def get_broker_credentials(self) -> Dict[str, Dict[str, str]]:
        """Get broker connection credentials"""
        return {
            'ibkr': {
                'paper_account': self.get_secret('IB_PAPER_ACCOUNT', settings.IB_PAPER_ACCOUNT),
                'live_account': self.get_secret('IB_LIVE_ACCOUNT', settings.IB_LIVE_ACCOUNT),
                'username': self.get_secret('IB_USERNAME', ''),
                'password': self.get_secret('IB_PASSWORD', ''),
            },
            'oanda': {
                'api_key': self.get_secret('OANDA_API_KEY', ''),
                'account_id': self.get_secret('OANDA_ACCOUNT_ID', ''),
            }
        }

# Global instance
secrets_manager = SecretsManager()