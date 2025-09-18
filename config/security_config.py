"""Security Configuration Module

Integrates encryption, secrets management, and certificate management
to provide comprehensive security configurations for all services.
"""

import os
import ssl
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import quote_plus

try:
    from pydantic_settings import BaseSettings
except ImportError:
    try:
        from pydantic import BaseSettings
    except ImportError:
        from pydantic.v1 import BaseSettings

from .encryption_config import encryption_settings, encryption_manager
from ..shared.utils.secrets_manager import secrets_manager
from ..shared.utils.certificate_manager import certificate_manager

logger = logging.getLogger(__name__)

class SecurityConfig:
    """Main security configuration class"""
    
    def __init__(self):
        self.encryption_settings = encryption_settings
        self.secrets_manager = secrets_manager
        self.certificate_manager = certificate_manager
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize security configuration"""
        if self._initialized:
            return
        
        try:
            # Initialize encryption manager
            encryption_manager.initialize()
            
            # Setup certificates if they don't exist
            self._setup_certificates_if_needed()
            
            # Validate security configuration
            self._validate_security_config()
            
            self._initialized = True
            logger.info("Security configuration initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize security configuration: {e}")
            raise
    
    def _setup_certificates_if_needed(self) -> None:
        """Setup certificates if they don't exist"""
        cert_dir = Path(encryption_settings.TLS_CERT_PATH).parent
        ca_cert_path = cert_dir / "ca.crt"
        
        if not ca_cert_path.exists():
            logger.info("Setting up default certificates...")
            certificate_manager.setup_default_certificates()
    
    def _validate_security_config(self) -> None:
        """Validate security configuration"""
        issues = []
        
        # Check if TLS is enabled
        if not encryption_settings.TLS_ENABLED:
            issues.append("TLS is disabled - this is not recommended for production")
        
        # Check certificate paths
        cert_paths = [
            encryption_settings.TLS_CERT_PATH,
            encryption_settings.TLS_KEY_PATH,
            encryption_settings.TLS_CA_PATH
        ]
        
        for path in cert_paths:
            if not Path(path).exists():
                issues.append(f"Certificate file not found: {path}")
        
        # Check encryption settings
        if not encryption_settings.DATABASE_ENCRYPTION_ENABLED:
            issues.append("Database encryption is disabled")
        
        if not encryption_settings.SECRETS_ENCRYPTION_ENABLED:
            issues.append("Secrets encryption is disabled")
        
        if issues:
            logger.warning("Security configuration issues found:")
            for issue in issues:
                logger.warning(f"  - {issue}")
    
    def get_database_config(self, service_name: str = "postgres") -> Dict[str, Any]:
        """Get secure database configuration"""
        credentials = secrets_manager.get_database_credentials()
        ssl_config = encryption_manager.get_database_ssl_config()
        
        config = {
            'host': credentials['host'],
            'port': int(credentials['port']),
            'database': credentials['database'],
            'username': credentials['username'],
            'password': credentials['password'],
        }
        
        # Add SSL configuration if enabled
        if encryption_settings.TLS_ENABLED:
            config.update(ssl_config)
        
        return config
    
    def get_database_url(self, service_name: str = "postgres", 
                        include_ssl: bool = True) -> str:
        """Get secure database URL with SSL parameters"""
        config = self.get_database_config(service_name)
        
        # URL encode password to handle special characters
        password = quote_plus(config['password']) if config['password'] else ''
        username = quote_plus(config['username'])
        
        base_url = f"postgresql://{username}:{password}@{config['host']}:{config['port']}/{config['database']}"
        
        if include_ssl and encryption_settings.TLS_ENABLED:
            ssl_params = [
                f"sslmode={config.get('sslmode', 'require')}",
            ]
            
            if config.get('sslcert'):
                ssl_params.append(f"sslcert={config['sslcert']}")
            if config.get('sslkey'):
                ssl_params.append(f"sslkey={config['sslkey']}")
            if config.get('sslrootcert'):
                ssl_params.append(f"sslrootcert={config['sslrootcert']}")
            
            base_url += "?" + "&".join(ssl_params)
        
        return base_url
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get secure Redis configuration"""
        config = {
            'host': secrets_manager.get_secret('REDIS_HOST', 'localhost'),
            'port': int(secrets_manager.get_secret('REDIS_PORT', '6379')),
            'password': secrets_manager.get_secret('REDIS_PASSWORD', ''),
            'db': int(secrets_manager.get_secret('REDIS_DB', '0')),
        }
        
        # Add SSL configuration if enabled
        if encryption_settings.REDIS_TLS_ENABLED:
            ssl_config = encryption_manager.get_redis_ssl_config()
            config.update(ssl_config)
        
        return config
    
    def get_kafka_config(self) -> Dict[str, Any]:
        """Get secure Kafka configuration"""
        config = {
            'bootstrap_servers': secrets_manager.get_secret(
                'KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'
            ),
            'client_id': 'ats-secure-client',
        }
        
        # Add SSL configuration if enabled
        if encryption_settings.KAFKA_SECURITY_PROTOCOL == 'SSL':
            ssl_config = encryption_manager.get_kafka_ssl_config()
            config.update(ssl_config)
        
        return config
    
    def get_api_security_config(self) -> Dict[str, Any]:
        """Get API security configuration"""
        return {
            'tls_enabled': encryption_settings.TLS_ENABLED,
            'tls_context': encryption_manager.get_tls_context(),
            'jwt_encryption_enabled': encryption_settings.JWT_ENCRYPTION_ENABLED,
            'api_encryption_enabled': encryption_settings.API_ENCRYPTION_ENABLED,
            'payload_encryption': encryption_settings.API_PAYLOAD_ENCRYPTION,
            'allowed_cipher_suites': encryption_settings.TLS_CIPHER_SUITES,
            'min_tls_version': encryption_settings.TLS_VERSION,
        }
    
    def get_ssl_context(self, purpose: str = 'server') -> ssl.SSLContext:
        """Create SSL context for secure connections"""
        if purpose == 'server':
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(
                encryption_settings.TLS_CERT_PATH,
                encryption_settings.TLS_KEY_PATH
            )
        else:  # client
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context.load_verify_locations(encryption_settings.TLS_CA_PATH)
        
        # Configure secure settings
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.maximum_version = ssl.TLSVersion.TLSv1_3
        
        # Set cipher suites
        if encryption_settings.TLS_CIPHER_SUITES:
            context.set_ciphers(':'.join(encryption_settings.TLS_CIPHER_SUITES))
        
        # Security options
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1
        context.options |= ssl.OP_SINGLE_DH_USE
        context.options |= ssl.OP_SINGLE_ECDH_USE
        
        return context
    
    def get_broker_config(self, broker_name: str) -> Dict[str, Any]:
        """Get secure broker configuration"""
        credentials = secrets_manager.get_broker_credentials()
        
        if broker_name.lower() == 'ibkr':
            return {
                'host': secrets_manager.get_secret('IB_HOST', '127.0.0.1'),
                'paper_port': int(secrets_manager.get_secret('IB_PAPER_PORT', '7497')),
                'live_port': int(secrets_manager.get_secret('IB_LIVE_PORT', '7496')),
                'paper_account': credentials['ibkr']['paper_account'],
                'live_account': credentials['ibkr']['live_account'],
                'username': credentials['ibkr']['username'],
                'password': credentials['ibkr']['password'],
                'tls_enabled': encryption_settings.TLS_ENABLED,
            }
        
        elif broker_name.lower() == 'oanda':
            return {
                'api_key': credentials['oanda']['api_key'],
                'account_id': credentials['oanda']['account_id'],
                'environment': secrets_manager.get_secret('OANDA_ENVIRONMENT', 'practice'),
                'tls_enabled': True,  # OANDA always uses HTTPS
            }
        
        else:
            raise ValueError(f"Unknown broker: {broker_name}")
    
    def get_data_feed_config(self) -> Dict[str, Any]:
        """Get secure data feed configuration"""
        api_keys = secrets_manager.get_api_keys()
        
        return {
            'encryption_enabled': encryption_settings.API_ENCRYPTION_ENABLED,
            'tls_enabled': encryption_settings.TLS_ENABLED,
            'api_keys': api_keys,
            'rate_limiting': {
                'enabled': True,
                'requests_per_second': 10,
                'burst_limit': 50,
            },
            'timeout_seconds': 30,
            'retry_attempts': 3,
            'ssl_verify': True,
        }
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring and logging security configuration"""
        return {
            'audit_logging_enabled': encryption_settings.ENCRYPTION_AUDIT_ENABLED,
            'log_encryption_enabled': encryption_settings.FILE_ENCRYPTION_ENABLED,
            'sensitive_data_masking': True,
            'security_event_alerting': True,
            'compliance_mode': encryption_settings.ENCRYPTION_COMPLIANCE_MODE,
            'log_retention_days': 90,
            'audit_trail_encryption': True,
        }
    
    def encrypt_sensitive_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive configuration values"""
        sensitive_keys = {
            'password', 'api_key', 'secret', 'token', 'key', 'credential',
            'auth', 'private', 'cert', 'ssl_key'
        }
        
        encrypted_config = {}
        
        for key, value in config.items():
            if isinstance(value, dict):
                encrypted_config[key] = self.encrypt_sensitive_config(value)
            elif isinstance(value, str) and any(sensitive in key.lower() for sensitive in sensitive_keys):
                if value:  # Only encrypt non-empty values
                    encrypted_config[key] = encryption_manager.encrypt_string(value)
                else:
                    encrypted_config[key] = value
            else:
                encrypted_config[key] = value
        
        return encrypted_config
    
    def decrypt_sensitive_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive configuration values"""
        sensitive_keys = {
            'password', 'api_key', 'secret', 'token', 'key', 'credential',
            'auth', 'private', 'cert', 'ssl_key'
        }
        
        decrypted_config = {}
        
        for key, value in config.items():
            if isinstance(value, dict):
                decrypted_config[key] = self.decrypt_sensitive_config(value)
            elif isinstance(value, str) and any(sensitive in key.lower() for sensitive in sensitive_keys):
                if value:  # Only decrypt non-empty values
                    try:
                        decrypted_config[key] = encryption_manager.decrypt_string(value)
                    except Exception:
                        # Value might not be encrypted
                        decrypted_config[key] = value
                else:
                    decrypted_config[key] = value
            else:
                decrypted_config[key] = value
        
        return decrypted_config
    
    def validate_certificate_expiry(self) -> List[Dict[str, Any]]:
        """Check all certificates for expiry and renewal needs"""
        return certificate_manager.list_certificates()
    
    def renew_expiring_certificates(self) -> Dict[str, bool]:
        """Renew certificates that are expiring soon"""
        certificates = self.validate_certificate_expiry()
        renewal_results = {}
        
        for cert in certificates:
            if cert.get('needs_renewal', False):
                cert_name = cert['name']
                logger.info(f"Renewing certificate: {cert_name}")
                success = certificate_manager.renew_certificate(cert_name)
                renewal_results[cert_name] = success
        
        return renewal_results
    
    def get_security_headers(self) -> Dict[str, str]:
        """Get security headers for HTTP responses"""
        return {
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self' wss: https:; frame-ancestors 'none';",
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=(), payment=(), usb=(), magnetometer=(), gyroscope=(), speaker=(), vibrate=(), fullscreen=(self), sync-xhr=()',
        }
    
    def get_cors_config(self) -> Dict[str, Any]:
        """Get CORS configuration"""
        allowed_origins = secrets_manager.get_secret(
            'ALLOWED_ORIGINS', 
            'http://localhost:3000,http://localhost:8080'
        ).split(',')
        
        return {
            'allow_origins': [origin.strip() for origin in allowed_origins],
            'allow_credentials': True,
            'allow_methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
            'allow_headers': [
                'Accept',
                'Accept-Language',
                'Content-Language',
                'Content-Type',
                'Authorization',
                'X-Requested-With',
                'X-API-Key',
            ],
            'expose_headers': ['X-Total-Count', 'X-Rate-Limit-Remaining'],
            'max_age': 86400,  # 24 hours
        }
    
    def get_rate_limiting_config(self) -> Dict[str, Any]:
        """Get rate limiting configuration"""
        return {
            'enabled': True,
            'default_rate': '100/minute',
            'burst_rate': '200/minute',
            'per_endpoint_limits': {
                '/api/auth/login': '5/minute',
                '/api/auth/register': '3/minute',
                '/api/trading/orders': '50/minute',
                '/api/market-data/quotes': '1000/minute',
            },
            'whitelist_ips': [],
            'blacklist_ips': [],
            'storage_backend': 'redis',
        }

# Global instance
security_config = SecurityConfig()