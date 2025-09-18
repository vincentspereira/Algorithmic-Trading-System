"""Encryption Configuration Module

Provides comprehensive encryption settings for data at rest and in transit,
including TLS/SSL configuration, secrets management, and key rotation.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import secrets

try:
    from pydantic_settings import BaseSettings
except ImportError:
    try:
        from pydantic import BaseSettings
    except ImportError:
        from pydantic.v1 import BaseSettings

class EncryptionSettings(BaseSettings):
    """Encryption configuration settings"""
    
    # Master encryption key settings
    MASTER_KEY_PATH: str = "/app/keys/master.key"
    MASTER_KEY_ENV: str = "ATS_MASTER_KEY"
    KEY_ROTATION_DAYS: int = 90
    
    # Data encryption at rest
    DATABASE_ENCRYPTION_ENABLED: bool = True
    DATABASE_ENCRYPTION_ALGORITHM: str = "AES-256-GCM"
    FILE_ENCRYPTION_ENABLED: bool = True
    BACKUP_ENCRYPTION_ENABLED: bool = True
    
    # TLS/SSL Configuration
    TLS_ENABLED: bool = True
    TLS_VERSION: str = "TLSv1.3"
    TLS_CERT_PATH: str = "/app/certs/server.crt"
    TLS_KEY_PATH: str = "/app/certs/server.key"
    TLS_CA_PATH: str = "/app/certs/ca.crt"
    TLS_VERIFY_MODE: str = "CERT_REQUIRED"
    
    # SSL Cipher suites (secure configurations)
    TLS_CIPHER_SUITES: List[str] = [
        "TLS_AES_256_GCM_SHA384",
        "TLS_CHACHA20_POLY1305_SHA256",
        "TLS_AES_128_GCM_SHA256",
        "ECDHE-RSA-AES256-GCM-SHA384",
        "ECDHE-RSA-AES128-GCM-SHA256"
    ]
    
    # Certificate settings
    CERT_AUTO_RENEWAL: bool = True
    CERT_RENEWAL_DAYS_BEFORE: int = 30
    CERT_KEY_SIZE: int = 4096
    CERT_VALIDITY_DAYS: int = 365
    
    # Secrets management
    SECRETS_BACKEND: str = "file"  # Options: file, vault, aws_secrets, azure_keyvault
    SECRETS_PATH: str = "/app/secrets"
    SECRETS_ENCRYPTION_ENABLED: bool = True
    
    # Vault configuration (if using HashiCorp Vault)
    VAULT_URL: str = "http://localhost:8200"
    VAULT_TOKEN: str = ""
    VAULT_MOUNT_POINT: str = "secret"
    VAULT_NAMESPACE: str = ""
    
    # AWS Secrets Manager (if using AWS)
    AWS_SECRETS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    
    # Azure Key Vault (if using Azure)
    AZURE_VAULT_URL: str = ""
    AZURE_CLIENT_ID: str = ""
    AZURE_CLIENT_SECRET: str = ""
    AZURE_TENANT_ID: str = ""
    
    # JWT Token encryption
    JWT_ENCRYPTION_ENABLED: bool = True
    JWT_ENCRYPTION_ALGORITHM: str = "A256GCM"
    JWT_KEY_ROTATION_HOURS: int = 24
    
    # API encryption
    API_ENCRYPTION_ENABLED: bool = True
    API_PAYLOAD_ENCRYPTION: bool = True
    API_HEADER_ENCRYPTION: bool = False
    
    # Database connection encryption
    DB_SSL_MODE: str = "require"
    DB_SSL_CERT: str = "/app/certs/client.crt"
    DB_SSL_KEY: str = "/app/certs/client.key"
    DB_SSL_ROOT_CERT: str = "/app/certs/ca.crt"
    
    # Redis encryption
    REDIS_TLS_ENABLED: bool = True
    REDIS_TLS_CERT_PATH: str = "/app/certs/redis-client.crt"
    REDIS_TLS_KEY_PATH: str = "/app/certs/redis-client.key"
    REDIS_TLS_CA_PATH: str = "/app/certs/redis-ca.crt"
    
    # Kafka encryption
    KAFKA_SECURITY_PROTOCOL: str = "SSL"
    KAFKA_SSL_CERT_PATH: str = "/app/certs/kafka-client.crt"
    KAFKA_SSL_KEY_PATH: str = "/app/certs/kafka-client.key"
    KAFKA_SSL_CA_PATH: str = "/app/certs/kafka-ca.crt"
    KAFKA_SSL_CHECK_HOSTNAME: bool = True
    
    # Audit and compliance
    ENCRYPTION_AUDIT_ENABLED: bool = True
    ENCRYPTION_COMPLIANCE_MODE: str = "FIPS-140-2"  # Options: FIPS-140-2, Common-Criteria
    
    model_config = {
        "extra": "allow",
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    }

class EncryptionManager:
    """Manages encryption operations and key management"""
    
    def __init__(self, settings: EncryptionSettings):
        self.settings = settings
        self._master_key: Optional[bytes] = None
        self._fernet: Optional[Fernet] = None
    
    def initialize(self) -> None:
        """Initialize encryption manager"""
        self._load_or_generate_master_key()
        self._setup_fernet()
    
    def _load_or_generate_master_key(self) -> None:
        """Load existing master key or generate new one"""
        # Try to load from environment variable first
        env_key = os.getenv(self.settings.MASTER_KEY_ENV)
        if env_key:
            self._master_key = base64.urlsafe_b64decode(env_key.encode())
            return
        
        # Try to load from file
        key_path = Path(self.settings.MASTER_KEY_PATH)
        if key_path.exists():
            with open(key_path, 'rb') as f:
                self._master_key = f.read()
            return
        
        # Generate new master key
        self._master_key = Fernet.generate_key()
        
        # Save to file (ensure directory exists)
        key_path.parent.mkdir(parents=True, exist_ok=True)
        with open(key_path, 'wb') as f:
            f.write(self._master_key)
        
        # Set restrictive permissions
        os.chmod(key_path, 0o600)
    
    def _setup_fernet(self) -> None:
        """Setup Fernet encryption instance"""
        if self._master_key:
            self._fernet = Fernet(self._master_key)
    
    def encrypt_data(self, data: bytes) -> bytes:
        """Encrypt data using Fernet"""
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")
        return self._fernet.encrypt(data)
    
    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Decrypt data using Fernet"""
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")
        return self._fernet.decrypt(encrypted_data)
    
    def encrypt_string(self, text: str) -> str:
        """Encrypt string and return base64 encoded result"""
        encrypted_bytes = self.encrypt_data(text.encode('utf-8'))
        return base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')
    
    def decrypt_string(self, encrypted_text: str) -> str:
        """Decrypt base64 encoded string"""
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_text.encode('utf-8'))
        decrypted_bytes = self.decrypt_data(encrypted_bytes)
        return decrypted_bytes.decode('utf-8')
    
    def generate_key_from_password(self, password: str, salt: bytes = None) -> bytes:
        """Generate encryption key from password using PBKDF2"""
        if salt is None:
            salt = secrets.token_bytes(32)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def rotate_master_key(self) -> None:
        """Rotate the master encryption key"""
        # This is a complex operation that would require:
        # 1. Generate new key
        # 2. Re-encrypt all data with new key
        # 3. Update key storage
        # Implementation would depend on specific requirements
        pass
    
    def get_tls_context(self) -> Dict:
        """Get TLS context configuration"""
        return {
            'ssl_version': self.settings.TLS_VERSION,
            'cert_file': self.settings.TLS_CERT_PATH,
            'key_file': self.settings.TLS_KEY_PATH,
            'ca_file': self.settings.TLS_CA_PATH,
            'verify_mode': self.settings.TLS_VERIFY_MODE,
            'cipher_suites': self.settings.TLS_CIPHER_SUITES
        }
    
    def get_database_ssl_config(self) -> Dict:
        """Get database SSL configuration"""
        return {
            'sslmode': self.settings.DB_SSL_MODE,
            'sslcert': self.settings.DB_SSL_CERT,
            'sslkey': self.settings.DB_SSL_KEY,
            'sslrootcert': self.settings.DB_SSL_ROOT_CERT
        }
    
    def get_kafka_ssl_config(self) -> Dict:
        """Get Kafka SSL configuration"""
        return {
            'security_protocol': self.settings.KAFKA_SECURITY_PROTOCOL,
            'ssl_certfile': self.settings.KAFKA_SSL_CERT_PATH,
            'ssl_keyfile': self.settings.KAFKA_SSL_KEY_PATH,
            'ssl_cafile': self.settings.KAFKA_SSL_CA_PATH,
            'ssl_check_hostname': self.settings.KAFKA_SSL_CHECK_HOSTNAME
        }
    
    def get_redis_ssl_config(self) -> Dict:
        """Get Redis SSL configuration"""
        return {
            'ssl': self.settings.REDIS_TLS_ENABLED,
            'ssl_certfile': self.settings.REDIS_TLS_CERT_PATH,
            'ssl_keyfile': self.settings.REDIS_TLS_KEY_PATH,
            'ssl_ca_certs': self.settings.REDIS_TLS_CA_PATH,
            'ssl_cert_reqs': 'required'
        }

# Global instances
encryption_settings = EncryptionSettings()
encryption_manager = EncryptionManager(encryption_settings)