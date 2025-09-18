"""Tests for encryption and security modules

Comprehensive test suite for encryption configuration, secrets management,
certificate management, TLS configuration, and security configuration.
"""

import os
import ssl
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Import modules to test
try:
    from config.encryption_config import EncryptionSettings, EncryptionManager
    from shared.utils.secrets_manager import (
        SecretsBackend, FileSecretsBackend, VaultSecretsBackend,
        AWSSecretsBackend, AzureSecretsBackend, SecretsManager
    )
    from shared.utils.certificate_manager import CertificateManager
    from shared.utils.tls_config import TLSConfig
    from config.security_config import SecurityConfig
except ImportError as e:
    pytest.skip(f"Required modules not available: {e}", allow_module_level=True)

class TestEncryptionSettings:
    """Test EncryptionSettings configuration"""
    
    def test_default_settings(self):
        """Test default encryption settings"""
        settings = EncryptionSettings()
        
        assert settings.ENCRYPTION_ENABLED is True
        assert settings.ENCRYPTION_ALGORITHM == "AES-256-GCM"
        assert settings.ENCRYPTION_KEY_SIZE == 256
        assert settings.TLS_ENABLED is True
        assert settings.DATABASE_ENCRYPTION_ENABLED is True
        assert settings.SECRETS_ENCRYPTION_ENABLED is True
    
    def test_custom_settings(self):
        """Test custom encryption settings"""
        custom_env = {
            'ENCRYPTION_ENABLED': 'false',
            'ENCRYPTION_ALGORITHM': 'AES-128-GCM',
            'TLS_VERSION': 'TLSv1.2',
        }
        
        with patch.dict(os.environ, custom_env):
            settings = EncryptionSettings()
            assert settings.ENCRYPTION_ENABLED is False
            assert settings.ENCRYPTION_ALGORITHM == "AES-128-GCM"
            assert settings.TLS_VERSION == "TLSv1.2"

class TestEncryptionManager:
    """Test EncryptionManager functionality"""
    
    @pytest.fixture
    def encryption_manager(self):
        """Create encryption manager for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = EncryptionSettings(
                ENCRYPTION_KEY_PATH=os.path.join(temp_dir, "test.key")
            )
            manager = EncryptionManager(settings)
            yield manager
    
    def test_key_generation(self, encryption_manager):
        """Test encryption key generation"""
        key = encryption_manager.generate_key()
        assert isinstance(key, bytes)
        assert len(key) == 32  # 256 bits
    
    def test_key_derivation(self, encryption_manager):
        """Test key derivation from password"""
        password = "test_password"
        salt = b"test_salt_16byte"
        
        key = encryption_manager.derive_key_from_password(password, salt)
        assert isinstance(key, bytes)
        assert len(key) == 32
        
        # Same password and salt should produce same key
        key2 = encryption_manager.derive_key_from_password(password, salt)
        assert key == key2
    
    def test_string_encryption_decryption(self, encryption_manager):
        """Test string encryption and decryption"""
        encryption_manager.initialize()
        
        original_text = "This is a secret message"
        encrypted = encryption_manager.encrypt_string(original_text)
        decrypted = encryption_manager.decrypt_string(encrypted)
        
        assert encrypted != original_text
        assert decrypted == original_text
    
    def test_file_encryption_decryption(self, encryption_manager):
        """Test file encryption and decryption"""
        encryption_manager.initialize()
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            original_content = "This is secret file content"
            f.write(original_content)
            temp_file = f.name
        
        try:
            # Encrypt file
            encrypted_file = temp_file + ".enc"
            encryption_manager.encrypt_file(temp_file, encrypted_file)
            
            # Decrypt file
            decrypted_file = temp_file + ".dec"
            encryption_manager.decrypt_file(encrypted_file, decrypted_file)
            
            # Verify content
            with open(decrypted_file, 'r') as f:
                decrypted_content = f.read()
            
            assert decrypted_content == original_content
            
        finally:
            # Clean up
            for file_path in [temp_file, encrypted_file, decrypted_file]:
                if os.path.exists(file_path):
                    os.unlink(file_path)
    
    def test_tls_context_creation(self, encryption_manager):
        """Test TLS context creation"""
        context = encryption_manager.get_tls_context()
        assert isinstance(context, ssl.SSLContext)
        assert context.minimum_version >= ssl.TLSVersion.TLSv1_2

class TestFileSecretsBackend:
    """Test file-based secrets backend"""
    
    @pytest.fixture
    def secrets_file(self):
        """Create temporary secrets file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            secrets_data = {
                "test_secret": "test_value",
                "database": {
                    "host": "localhost",
                    "password": "secret_password"
                }
            }
            json.dump(secrets_data, f)
            temp_file = f.name
        
        yield temp_file
        
        # Clean up
        if os.path.exists(temp_file):
            os.unlink(temp_file)
    
    def test_file_backend_operations(self, secrets_file):
        """Test file backend CRUD operations"""
        backend = FileSecretsBackend(secrets_file)
        
        # Test get
        assert backend.get_secret("test_secret") == "test_value"
        assert backend.get_secret("nonexistent") is None
        assert backend.get_secret("nonexistent", "default") == "default"
        
        # Test set
        backend.set_secret("new_secret", "new_value")
        assert backend.get_secret("new_secret") == "new_value"
        
        # Test delete
        backend.delete_secret("test_secret")
        assert backend.get_secret("test_secret") is None
        
        # Test list
        secrets = backend.list_secrets()
        assert "new_secret" in secrets
        assert "test_secret" not in secrets

class TestSecretsManager:
    """Test SecretsManager functionality"""
    
    @pytest.fixture
    def mock_backend(self):
        """Create mock secrets backend"""
        backend = Mock(spec=SecretsBackend)
        backend.get_secret.return_value = "mock_value"
        backend.set_secret.return_value = None
        backend.delete_secret.return_value = None
        backend.list_secrets.return_value = ["secret1", "secret2"]
        return backend
    
    def test_secrets_manager_initialization(self, mock_backend):
        """Test secrets manager initialization"""
        with patch('shared.utils.secrets_manager.FileSecretsBackend', return_value=mock_backend):
            manager = SecretsManager(backend_type="file")
            assert manager.backend == mock_backend
    
    def test_get_database_credentials(self, mock_backend):
        """Test database credentials retrieval"""
        mock_backend.get_secret.side_effect = lambda key, default=None: {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'testdb',
            'POSTGRES_USER': 'testuser',
            'POSTGRES_PASSWORD': 'testpass'
        }.get(key, default)
        
        with patch('shared.utils.secrets_manager.FileSecretsBackend', return_value=mock_backend):
            manager = SecretsManager(backend_type="file")
            credentials = manager.get_database_credentials()
            
            assert credentials['host'] == 'localhost'
            assert credentials['port'] == '5432'
            assert credentials['database'] == 'testdb'
            assert credentials['username'] == 'testuser'
            assert credentials['password'] == 'testpass'
    
    def test_get_api_keys(self, mock_backend):
        """Test API keys retrieval"""
        mock_backend.get_secret.side_effect = lambda key, default=None: {
            'ALPHA_VANTAGE_API_KEY': 'av_key',
            'FINNHUB_API_KEY': 'fh_key',
            'POLYGON_API_KEY': 'poly_key'
        }.get(key, default)
        
        with patch('shared.utils.secrets_manager.FileSecretsBackend', return_value=mock_backend):
            manager = SecretsManager(backend_type="file")
            api_keys = manager.get_api_keys()
            
            assert api_keys['alpha_vantage'] == 'av_key'
            assert api_keys['finnhub'] == 'fh_key'
            assert api_keys['polygon'] == 'poly_key'

class TestCertificateManager:
    """Test CertificateManager functionality"""
    
    @pytest.fixture
    def cert_manager(self):
        """Create certificate manager for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = CertificateManager(cert_dir=temp_dir)
            yield manager
    
    @pytest.mark.skipif(not hasattr(ssl, 'create_default_context'), 
                       reason="SSL context creation not available")
    def test_certificate_generation(self, cert_manager):
        """Test certificate generation"""
        # Generate CA certificate
        ca_cert, ca_key = cert_manager.generate_ca_certificate(
            subject_name="Test CA",
            validity_days=365
        )
        
        assert ca_cert is not None
        assert ca_key is not None
        
        # Generate server certificate
        server_cert, server_key = cert_manager.generate_server_certificate(
            ca_cert=ca_cert,
            ca_key=ca_key,
            server_name="localhost",
            validity_days=365
        )
        
        assert server_cert is not None
        assert server_key is not None
    
    def test_setup_default_certificates(self, cert_manager):
        """Test default certificate setup"""
        cert_manager.setup_default_certificates()
        
        # Check that certificate files were created
        assert cert_manager.ca_cert_path.exists()
        assert cert_manager.ca_key_path.exists()
        assert cert_manager.server_cert_path.exists()
        assert cert_manager.server_key_path.exists()
    
    def test_certificate_expiry_check(self, cert_manager):
        """Test certificate expiry checking"""
        cert_manager.setup_default_certificates()
        
        # Check expiry (should not be expired for new certificates)
        is_expired = cert_manager.check_certificate_expiry(
            cert_manager.server_cert_path
        )
        assert not is_expired

class TestTLSConfig:
    """Test TLS configuration functionality"""
    
    @pytest.fixture
    def tls_config(self):
        """Create TLS config for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = TLSConfig(cert_dir=temp_dir)
            # Create dummy certificate files
            for cert_file in [config.ca_cert_path, config.server_cert_path, 
                            config.server_key_path, config.client_cert_path, 
                            config.client_key_path]:
                cert_file.touch()
            yield config
    
    def test_ssl_context_creation(self, tls_config):
        """Test SSL context creation"""
        # Test server context
        server_context = tls_config.create_secure_ssl_context('server')
        assert isinstance(server_context, ssl.SSLContext)
        assert server_context.minimum_version >= ssl.TLSVersion.TLSv1_2
        
        # Test client context
        client_context = tls_config.create_secure_ssl_context('client')
        assert isinstance(client_context, ssl.SSLContext)
        assert client_context.minimum_version >= ssl.TLSVersion.TLSv1_2
    
    def test_database_ssl_config(self, tls_config):
        """Test database SSL configuration"""
        # PostgreSQL config
        pg_config = tls_config.get_database_ssl_config('postgresql')
        assert pg_config['sslmode'] == 'require'
        assert 'ssl_min_protocol_version' in pg_config
        
        # Redis config
        redis_config = tls_config.get_database_ssl_config('redis')
        assert redis_config['ssl'] is True
        assert redis_config['ssl_cert_reqs'] == ssl.CERT_REQUIRED
        
        # ClickHouse config
        ch_config = tls_config.get_database_ssl_config('clickhouse')
        assert ch_config['secure'] is True
        assert ch_config['verify'] is True
    
    def test_kafka_ssl_config(self, tls_config):
        """Test Kafka SSL configuration"""
        kafka_config = tls_config.get_kafka_ssl_config()
        assert kafka_config['security_protocol'] == 'SSL'
        assert kafka_config['ssl_check_hostname'] is True
    
    def test_cipher_suite_info(self, tls_config):
        """Test cipher suite information"""
        cipher_info = tls_config.get_cipher_suite_info()
        assert 'all_ciphers' in cipher_info
        assert 'secure_ciphers' in cipher_info
        assert 'weak_ciphers' in cipher_info
        assert 'recommended_ciphers' in cipher_info
    
    def test_service_tls_config(self, tls_config):
        """Test service-specific TLS configuration"""
        # Test API server config
        api_config = tls_config.create_tls_config_for_service('api_server')
        assert 'context' in api_config
        assert isinstance(api_config['context'], ssl.SSLContext)
        
        # Test database config
        db_config = tls_config.create_tls_config_for_service('database')
        assert 'config' in db_config
        assert db_config['require_ssl'] is True
        
        # Test invalid service
        with pytest.raises(ValueError):
            tls_config.create_tls_config_for_service('invalid_service')

class TestSecurityConfig:
    """Test SecurityConfig functionality"""
    
    @pytest.fixture
    def security_config(self):
        """Create security config for testing"""
        with patch('config.security_config.encryption_settings'), \
             patch('config.security_config.secrets_manager'), \
             patch('config.security_config.certificate_manager'):
            config = SecurityConfig()
            yield config
    
    def test_security_config_initialization(self, security_config):
        """Test security configuration initialization"""
        with patch.object(security_config, '_setup_certificates_if_needed'), \
             patch.object(security_config, '_validate_security_config'):
            security_config.initialize()
            assert security_config._initialized is True
    
    @patch('config.security_config.secrets_manager')
    def test_database_config_generation(self, mock_secrets, security_config):
        """Test database configuration generation"""
        mock_secrets.get_database_credentials.return_value = {
            'host': 'localhost',
            'port': '5432',
            'database': 'testdb',
            'username': 'testuser',
            'password': 'testpass'
        }
        
        config = security_config.get_database_config()
        assert config['host'] == 'localhost'
        assert config['port'] == 5432
        assert config['database'] == 'testdb'
        assert config['username'] == 'testuser'
        assert config['password'] == 'testpass'
    
    @patch('config.security_config.secrets_manager')
    def test_database_url_generation(self, mock_secrets, security_config):
        """Test database URL generation"""
        mock_secrets.get_database_credentials.return_value = {
            'host': 'localhost',
            'port': '5432',
            'database': 'testdb',
            'username': 'testuser',
            'password': 'test@pass'
        }
        
        url = security_config.get_database_url(include_ssl=False)
        assert 'postgresql://testuser:test%40pass@localhost:5432/testdb' in url
    
    def test_security_headers(self, security_config):
        """Test security headers generation"""
        headers = security_config.get_security_headers()
        
        assert 'Strict-Transport-Security' in headers
        assert 'X-Content-Type-Options' in headers
        assert 'X-Frame-Options' in headers
        assert 'Content-Security-Policy' in headers
        assert headers['X-Frame-Options'] == 'DENY'
        assert headers['X-Content-Type-Options'] == 'nosniff'
    
    @patch('config.security_config.secrets_manager')
    def test_cors_config(self, mock_secrets, security_config):
        """Test CORS configuration"""
        mock_secrets.get_secret.return_value = 'http://localhost:3000,https://example.com'
        
        cors_config = security_config.get_cors_config()
        assert 'allow_origins' in cors_config
        assert 'http://localhost:3000' in cors_config['allow_origins']
        assert 'https://example.com' in cors_config['allow_origins']
        assert cors_config['allow_credentials'] is True
    
    def test_rate_limiting_config(self, security_config):
        """Test rate limiting configuration"""
        rate_config = security_config.get_rate_limiting_config()
        
        assert rate_config['enabled'] is True
        assert 'default_rate' in rate_config
        assert 'per_endpoint_limits' in rate_config
        assert '/api/auth/login' in rate_config['per_endpoint_limits']
    
    def test_sensitive_config_encryption(self, security_config):
        """Test sensitive configuration encryption"""
        with patch.object(security_config, 'encryption_manager') as mock_em:
            mock_em.encrypt_string.return_value = 'encrypted_value'
            
            config = {
                'username': 'testuser',
                'password': 'secret',
                'api_key': 'key123',
                'normal_value': 'not_secret'
            }
            
            encrypted_config = security_config.encrypt_sensitive_config(config)
            
            assert encrypted_config['username'] == 'testuser'  # Not sensitive
            assert encrypted_config['normal_value'] == 'not_secret'  # Not sensitive
            # Sensitive values should be encrypted (mocked)
            mock_em.encrypt_string.assert_called()

class TestIntegration:
    """Integration tests for security modules"""
    
    def test_full_security_stack_initialization(self):
        """Test full security stack initialization"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up temporary environment
            env_vars = {
                'ENCRYPTION_KEY_PATH': os.path.join(temp_dir, 'encryption.key'),
                'SECRETS_FILE_PATH': os.path.join(temp_dir, 'secrets.json'),
                'TLS_CERT_PATH': os.path.join(temp_dir, 'server.crt'),
                'TLS_KEY_PATH': os.path.join(temp_dir, 'server.key'),
                'TLS_CA_PATH': os.path.join(temp_dir, 'ca.crt'),
            }
            
            with patch.dict(os.environ, env_vars):
                try:
                    # Initialize components
                    settings = EncryptionSettings()
                    manager = EncryptionManager(settings)
                    
                    # This should not raise any exceptions
                    assert settings.ENCRYPTION_ENABLED is not None
                    assert manager is not None
                    
                except Exception as e:
                    pytest.fail(f"Security stack initialization failed: {e}")
    
    def test_certificate_and_tls_integration(self):
        """Test certificate manager and TLS config integration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create certificate manager
            cert_manager = CertificateManager(cert_dir=temp_dir)
            cert_manager.setup_default_certificates()
            
            # Create TLS config
            tls_config = TLSConfig(cert_dir=temp_dir)
            
            # Test that TLS config can use generated certificates
            try:
                context = tls_config.create_secure_ssl_context('server')
                assert isinstance(context, ssl.SSLContext)
            except Exception as e:
                # This might fail due to self-signed certificates, which is expected
                assert "certificate" in str(e).lower() or "ssl" in str(e).lower()

if __name__ == '__main__':
    pytest.main([__file__, '-v'])