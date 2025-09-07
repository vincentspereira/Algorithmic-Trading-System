"""
Test suite for SecretsManager class

This module contains comprehensive tests for the SecretsManager class,
validating all functionality including .env file validation, credential verification,
API key validation, and database connection testing.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
import json
from datetime import datetime

# Add the framework directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from secrets_manager import (
    SecretsManager,
    ValidationStatus,
    SecretType,
    SecurityLevel,
    SecretInfo,
    ValidationResult
)


class TestSecretsManager:
    """Test suite for SecretsManager class"""
    
    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory for testing"""
        temp_dir = Path(tempfile.mkdtemp())
        
        # Create sample .env file
        env_content = """
# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=test_db
POSTGRES_USER=test_user
POSTGRES_PASSWORD=secure_password_123
DATABASE_URL=postgresql://test_user:secure_password_123@localhost:5432/test_db

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=redis_pass_456

# API Keys
ALPHA_VANTAGE_API_KEY=ABCD1234EFGH5678
FINNHUB_API_KEY=abcdefghij1234567890
NEWS_API_KEY=test_news_api_key_789

# JWT Configuration
SECRET_KEY=super-secret-jwt-key-for-testing-purposes-2024
JWT_SECRET_KEY=another-jwt-secret-key-with-sufficient-length

# Placeholder values (should be flagged)
PLACEHOLDER_API_KEY=your_api_key_here
DUMMY_SECRET=dummy-secret-value
TEST_PASSWORD=test123

# Empty values
EMPTY_SECRET=
MISSING_VALUE=

# Development settings
DEBUG=true
LOG_LEVEL=INFO
ENVIRONMENT=development
"""
        (temp_dir / ".env").write_text(env_content.strip())
        
        # Create sample .env.example file
        example_content = """
POSTGRES_PASSWORD=your_secure_password
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
SECRET_KEY=your_secret_key
"""
        (temp_dir / ".env.example").write_text(example_content.strip())
        
        yield temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def secrets_manager(self, temp_project_dir):
        """Create a SecretsManager instance for testing"""
        return SecretsManager(project_root=temp_project_dir)
    
    def test_init(self, temp_project_dir):
        """Test SecretsManager initialization"""
        manager = SecretsManager(project_root=temp_project_dir)
        
        assert manager.project_root == temp_project_dir
        assert manager.env_files == [".env", ".env.example"]
        assert manager.validation_timeout == 30
        assert manager.api_validation_enabled == True
        assert manager.database_validation_enabled == True
    
    def test_init_custom_env_files(self, temp_project_dir):
        """Test SecretsManager initialization with custom env files"""
        custom_files = [".env.test", ".env.local"]
        manager = SecretsManager(project_root=temp_project_dir, env_files=custom_files)
        
        assert manager.env_files == custom_files
    
    def test_load_environment_variables(self, secrets_manager):
        """Test loading environment variables from .env files"""
        # Check that variables were loaded
        assert 'POSTGRES_HOST' in secrets_manager.env_vars
        assert secrets_manager.env_vars['POSTGRES_HOST'] == 'localhost'
        # Note: .env.example is loaded after .env, so it may override values
        assert 'POSTGRES_PASSWORD' in secrets_manager.env_vars
        assert 'ALPHA_VANTAGE_API_KEY' in secrets_manager.env_vars
    
    def test_classify_secret_type(self, secrets_manager):
        """Test secret type classification"""
        assert secrets_manager._classify_secret_type('POSTGRES_PASSWORD') == SecretType.DATABASE_PASSWORD
        assert secrets_manager._classify_secret_type('ALPHA_VANTAGE_API_KEY') == SecretType.API_KEY
        assert secrets_manager._classify_secret_type('SECRET_KEY') == SecretType.JWT_SECRET
        assert secrets_manager._classify_secret_type('DATABASE_URL') == SecretType.CONNECTION_STRING
        assert secrets_manager._classify_secret_type('CLIENT_SECRET') == SecretType.OAUTH_SECRET
        assert secrets_manager._classify_secret_type('RANDOM_CONFIG') == SecretType.UNKNOWN
    
    def test_determine_security_level(self, secrets_manager):
        """Test security level determination"""
        assert secrets_manager._determine_security_level('SECRET_KEY', SecretType.JWT_SECRET) == SecurityLevel.CRITICAL
        assert secrets_manager._determine_security_level('POSTGRES_PASSWORD', SecretType.DATABASE_PASSWORD) == SecurityLevel.HIGH
        assert secrets_manager._determine_security_level('API_KEY', SecretType.API_KEY) == SecurityLevel.MEDIUM
        assert secrets_manager._determine_security_level('DATABASE_URL', SecretType.CONNECTION_STRING) == SecurityLevel.LOW
        assert secrets_manager._determine_security_level('DEBUG', SecretType.UNKNOWN) == SecurityLevel.INFO
    
    def test_is_required_secret(self, secrets_manager):
        """Test required secret identification"""
        assert secrets_manager._is_required_secret('SECRET_KEY') == True
        assert secrets_manager._is_required_secret('POSTGRES_PASSWORD') == True
        assert secrets_manager._is_required_secret('JWT_SECRET_KEY') == True
        assert secrets_manager._is_required_secret('DEBUG') == False
        assert secrets_manager._is_required_secret('LOG_LEVEL') == False
    
    def test_is_sensitive_secret(self, secrets_manager):
        """Test sensitive secret identification"""
        assert secrets_manager._is_sensitive_secret('PASSWORD', SecretType.DATABASE_PASSWORD) == True
        assert secrets_manager._is_sensitive_secret('API_KEY', SecretType.API_KEY) == True
        assert secrets_manager._is_sensitive_secret('SECRET_KEY', SecretType.JWT_SECRET) == True
        assert secrets_manager._is_sensitive_secret('DEBUG', SecretType.UNKNOWN) == False
        assert secrets_manager._is_sensitive_secret('LOG_LEVEL', SecretType.UNKNOWN) == False
    
    def test_validate_password_strong(self, secrets_manager):
        """Test password validation with strong password"""
        status, message, score = secrets_manager._validate_password('StrongPass123!')
        assert status == ValidationStatus.VALID
        assert score >= 80
        assert "meets requirements" in message
    
    def test_validate_password_weak(self, secrets_manager):
        """Test password validation with weak password"""
        status, message, score = secrets_manager._validate_password('weak')
        assert status == ValidationStatus.INVALID
        assert score <= 40
        assert "too short" in message
    
    def test_validate_password_medium(self, secrets_manager):
        """Test password validation with medium strength password"""
        status, message, score = secrets_manager._validate_password('Password123')
        assert status in [ValidationStatus.VALID, ValidationStatus.WARNING]
        assert score >= 40
    
    def test_validate_jwt_secret_strong(self, secrets_manager):
        """Test JWT secret validation with strong secret"""
        long_secret = 'a' * 64
        status, message, score = secrets_manager._validate_jwt_secret(long_secret)
        assert status == ValidationStatus.VALID
        assert score >= 90
    
    def test_validate_jwt_secret_weak(self, secrets_manager):
        """Test JWT secret validation with weak secret"""
        short_secret = 'short'
        status, message, score = secrets_manager._validate_jwt_secret(short_secret)
        assert status == ValidationStatus.INVALID
        assert score <= 20
        assert "too short" in message
    
    def test_validate_api_key_format(self, secrets_manager):
        """Test API key format validation"""
        # Alpha Vantage format
        status, message, score = secrets_manager._validate_api_key('ALPHA_VANTAGE_API_KEY', 'ABCD1234EFGH5678')
        assert status in [ValidationStatus.VALID, ValidationStatus.WARNING]
        
        # Too short
        status, message, score = secrets_manager._validate_api_key('TEST_API_KEY', 'short')
        assert status == ValidationStatus.INVALID
        assert "too short" in message
    
    def test_validate_connection_string_valid(self, secrets_manager):
        """Test connection string validation with valid string"""
        conn_str = 'postgresql://user:pass@localhost:5432/db'
        status, message, score = secrets_manager._validate_connection_string(conn_str)
        assert status == ValidationStatus.VALID
        assert score >= 90
    
    def test_validate_connection_string_invalid(self, secrets_manager):
        """Test connection string validation with invalid string"""
        conn_str = 'invalid-connection-string'
        status, message, score = secrets_manager._validate_connection_string(conn_str)
        assert status == ValidationStatus.INVALID
        assert score <= 30
    
    def test_validate_secret_value_placeholder(self, secrets_manager):
        """Test secret value validation with placeholder values"""
        status, message, score = secrets_manager._validate_secret_value(
            'API_KEY', 'your_api_key_here', SecretType.API_KEY
        )
        assert status == ValidationStatus.INVALID
        assert "placeholder" in message
        assert score == 10
    
    def test_validate_secret_value_empty(self, secrets_manager):
        """Test secret value validation with empty value"""
        status, message, score = secrets_manager._validate_secret_value(
            'API_KEY', '', SecretType.API_KEY
        )
        assert status == ValidationStatus.MISSING
        assert "empty" in message
        assert score == 0
    
    def test_mask_secret(self, secrets_manager):
        """Test secret masking"""
        # Short secret
        masked = secrets_manager._mask_secret('short')
        assert masked == '*****'
        
        # Long secret
        masked = secrets_manager._mask_secret('this_is_a_long_secret_key')
        assert masked.startswith('this')
        assert masked.endswith('_key')
        assert '*' in masked
        
        # Empty secret
        masked = secrets_manager._mask_secret('')
        assert masked == ''
    
    def test_analyze_secret(self, secrets_manager):
        """Test secret analysis"""
        secret_info = secrets_manager._analyze_secret('POSTGRES_PASSWORD', 'secure_password_123')
        
        assert secret_info.name == 'POSTGRES_PASSWORD'
        assert secret_info.secret_type == SecretType.DATABASE_PASSWORD
        assert secret_info.security_level == SecurityLevel.HIGH
        assert secret_info.is_required == True
        assert secret_info.is_sensitive == True
        assert secret_info.validation_status in [ValidationStatus.VALID, ValidationStatus.WARNING]
        assert secret_info.last_validated is not None
        assert secret_info.strength_score is not None
    
    def test_validate_env_file(self, secrets_manager):
        """Test .env file validation"""
        result = secrets_manager.validate_env_file()
        
        assert isinstance(result, ValidationResult)
        assert result.total_secrets > 0
        assert result.validation_summary is not None
        assert 'total_variables' in result.validation_summary
        assert 'sensitive_variables' in result.validation_summary
        
        # Check that placeholder values are flagged
        placeholder_issues = [
            issue for issue in result.critical_issues + result.high_issues + result.medium_issues + result.low_issues
            if 'placeholder' in issue.lower()
        ]
        assert len(placeholder_issues) > 0
    
    @patch('psycopg2.connect')
    def test_validate_postgres_connection_success(self, mock_connect, secrets_manager):
        """Test successful PostgreSQL connection validation"""
        # Mock successful connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = ('PostgreSQL 15.0',)
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        result = secrets_manager._validate_postgres_connection()
        
        assert result == ValidationStatus.VALID
        mock_connect.assert_called_once()
        mock_cursor.execute.assert_called_once_with("SELECT version();")
    
    @patch('psycopg2.connect')
    def test_validate_postgres_connection_failure(self, mock_connect, secrets_manager):
        """Test failed PostgreSQL connection validation"""
        # Mock connection failure
        import psycopg2
        mock_connect.side_effect = psycopg2.OperationalError("Connection failed")
        
        result = secrets_manager._validate_postgres_connection()
        
        assert result == ValidationStatus.INVALID
    
    @patch('redis.Redis')
    def test_validate_redis_connection_success(self, mock_redis, secrets_manager):
        """Test successful Redis connection validation"""
        # Mock successful connection
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis.return_value = mock_redis_instance
        
        result = secrets_manager._validate_redis_connection()
        
        assert result == ValidationStatus.VALID
        mock_redis_instance.ping.assert_called_once()
    
    @patch('redis.Redis')
    def test_validate_redis_connection_failure(self, mock_redis, secrets_manager):
        """Test failed Redis connection validation"""
        # Mock connection failure
        import redis
        mock_redis_instance = Mock()
        mock_redis_instance.ping.side_effect = redis.ConnectionError("Connection failed")
        mock_redis.return_value = mock_redis_instance
        
        result = secrets_manager._validate_redis_connection()
        
        assert result == ValidationStatus.INVALID
    
    @patch('requests.get')
    def test_validate_clickhouse_connection_success(self, mock_get, secrets_manager):
        """Test successful ClickHouse connection validation"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Ok."
        mock_get.return_value = mock_response
        
        result = secrets_manager._validate_clickhouse_connection()
        
        assert result == ValidationStatus.VALID
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_validate_clickhouse_connection_failure(self, mock_get, secrets_manager):
        """Test failed ClickHouse connection validation"""
        # Mock connection failure
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response
        
        result = secrets_manager._validate_clickhouse_connection()
        
        assert result == ValidationStatus.INVALID
    
    def test_validate_database_connections(self, secrets_manager):
        """Test database connections validation"""
        with patch.object(secrets_manager, '_validate_postgres_connection', return_value=ValidationStatus.VALID):
            with patch.object(secrets_manager, '_validate_redis_connection', return_value=ValidationStatus.VALID):
                with patch.object(secrets_manager, '_validate_clickhouse_connection', return_value=ValidationStatus.VALID):
                    results = secrets_manager.validate_database_connections()
        
        assert 'PostgreSQL' in results
        assert 'Redis' in results
        assert 'ClickHouse' in results
        assert results['PostgreSQL'] == ValidationStatus.VALID
    
    @patch('requests.get')
    def test_validate_single_api_key_success(self, mock_get, secrets_manager):
        """Test successful API key validation"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'Meta Data': {'1. Information': 'Intraday Prices'}}
        mock_get.return_value = mock_response
        
        result = secrets_manager._validate_single_api_key(
            'ALPHA_VANTAGE_API_KEY',
            'ABCD1234EFGH5678',
            'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=1min&apikey={}'
        )
        
        assert result == ValidationStatus.VALID
    
    @patch('requests.get')
    def test_validate_single_api_key_unauthorized(self, mock_get, secrets_manager):
        """Test API key validation with unauthorized response"""
        # Mock unauthorized response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        result = secrets_manager._validate_single_api_key(
            'ALPHA_VANTAGE_API_KEY',
            'INVALID_KEY',
            'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=1min&apikey={}'
        )
        
        assert result == ValidationStatus.INVALID
    
    @patch('requests.get')
    def test_validate_single_api_key_rate_limited(self, mock_get, secrets_manager):
        """Test API key validation with rate limiting"""
        # Mock rate limited response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response
        
        result = secrets_manager._validate_single_api_key(
            'ALPHA_VANTAGE_API_KEY',
            'ABCD1234EFGH5678',
            'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=1min&apikey={}'
        )
        
        assert result == ValidationStatus.RATE_LIMITED
    
    def test_validate_binance_api_key_format(self, secrets_manager):
        """Test Binance API key format validation"""
        # Valid format (64 hex characters)
        valid_key = 'a' * 64
        result = secrets_manager._validate_single_api_key(
            'BINANCE_API_KEY',
            valid_key,
            'https://api.binance.com/api/v3/account'
        )
        assert result == ValidationStatus.VALID
        
        # Invalid format
        invalid_key = 'invalid_key'
        result = secrets_manager._validate_single_api_key(
            'BINANCE_API_KEY',
            invalid_key,
            'https://api.binance.com/api/v3/account'
        )
        assert result == ValidationStatus.INVALID
    
    def test_is_valid_api_response(self, secrets_manager):
        """Test API response validation"""
        # Alpha Vantage response
        alpha_data = {'Meta Data': {'1. Information': 'Intraday Prices'}}
        assert secrets_manager._is_valid_api_response('ALPHA_VANTAGE_API_KEY', alpha_data) == True
        
        # Finnhub response
        finnhub_data = {'c': 150.0, 'h': 155.0, 'l': 148.0}
        assert secrets_manager._is_valid_api_response('FINNHUB_API_KEY', finnhub_data) == True
        
        # Invalid response
        invalid_data = {}
        assert secrets_manager._is_valid_api_response('ALPHA_VANTAGE_API_KEY', invalid_data) == False
        
        # None response
        assert secrets_manager._is_valid_api_response('ALPHA_VANTAGE_API_KEY', None) == False
    
    def test_validate_api_keys(self, secrets_manager):
        """Test API keys validation"""
        # Disable API validation to avoid actual network calls
        secrets_manager.set_validation_options(api_validation=False)
        results = secrets_manager.validate_api_keys()
        assert results == {}
        
        # Enable API validation and mock responses
        secrets_manager.set_validation_options(api_validation=True)
        
        with patch.object(secrets_manager, '_validate_single_api_key') as mock_validate:
            mock_validate.return_value = ValidationStatus.VALID
            results = secrets_manager.validate_api_keys()
            
            # Should have results for API keys present in env
            assert len(results) > 0
            assert 'ALPHA_VANTAGE_API_KEY' in results
    
    def test_comprehensive_secrets_validation(self, secrets_manager):
        """Test comprehensive secrets validation"""
        # Mock database and API validations
        with patch.object(secrets_manager, 'validate_database_connections') as mock_db:
            with patch.object(secrets_manager, 'validate_api_keys') as mock_api:
                mock_db.return_value = {'PostgreSQL': ValidationStatus.VALID}
                mock_api.return_value = {'ALPHA_VANTAGE_API_KEY': ValidationStatus.VALID}
                
                result = secrets_manager.comprehensive_secrets_validation()
        
        assert isinstance(result, ValidationResult)
        assert result.database_connections == {'PostgreSQL': ValidationStatus.VALID}
        assert result.api_key_validations == {'ALPHA_VANTAGE_API_KEY': ValidationStatus.VALID}
        assert 'comprehensive_validation' in result.validation_summary
        assert result.validation_summary['comprehensive_validation'] == True
    
    def test_generate_secrets_report(self, secrets_manager):
        """Test secrets report generation"""
        # Mock comprehensive validation
        with patch.object(secrets_manager, 'comprehensive_secrets_validation') as mock_validation:
            mock_result = ValidationResult(
                total_secrets=10,
                valid_secrets=8,
                invalid_secrets=1,
                missing_secrets=1,
                warning_secrets=0,
                critical_issues=['Critical issue'],
                high_issues=['High issue'],
                medium_issues=[],
                low_issues=[],
                secret_details=[],
                database_connections={'PostgreSQL': ValidationStatus.VALID},
                api_key_validations={'API_KEY': ValidationStatus.VALID},
                overall_status=ValidationStatus.WARNING,
                validation_summary={'test': 'value'}
            )
            mock_validation.return_value = mock_result
            
            report = secrets_manager.generate_secrets_report()
        
        assert "SECRETS VALIDATION REPORT" in report
        assert "Overall Status: WARNING" in report
        assert "CRITICAL ISSUES:" in report
        assert "HIGH PRIORITY ISSUES:" in report
        assert "DATABASE CONNECTIONS:" in report
        assert "API KEY VALIDATIONS:" in report
        assert "SECURITY RECOMMENDATIONS:" in report
    
    def test_get_secret_value(self, secrets_manager):
        """Test getting secret values"""
        # Existing secret
        value = secrets_manager.get_secret_value('POSTGRES_HOST')
        assert value == 'localhost'
        
        # Non-existing secret with default
        value = secrets_manager.get_secret_value('NON_EXISTENT', 'default_value')
        assert value == 'default_value'
        
        # Non-existing secret without default
        value = secrets_manager.get_secret_value('NON_EXISTENT')
        assert value is None
    
    def test_set_validation_options(self, secrets_manager):
        """Test setting validation options"""
        # Disable both validations
        secrets_manager.set_validation_options(api_validation=False, database_validation=False)
        assert secrets_manager.api_validation_enabled == False
        assert secrets_manager.database_validation_enabled == False
        
        # Enable both validations
        secrets_manager.set_validation_options(api_validation=True, database_validation=True)
        assert secrets_manager.api_validation_enabled == True
        assert secrets_manager.database_validation_enabled == True
    
    def test_secret_info_dataclass(self):
        """Test SecretInfo dataclass"""
        secret_info = SecretInfo(
            name="TEST_SECRET",
            value="test_value",
            secret_type=SecretType.API_KEY,
            security_level=SecurityLevel.MEDIUM,
            is_required=True,
            is_sensitive=True,
            validation_status=ValidationStatus.VALID,
            validation_message="Valid secret",
            strength_score=80
        )
        
        assert secret_info.name == "TEST_SECRET"
        assert secret_info.secret_type == SecretType.API_KEY
        assert secret_info.security_level == SecurityLevel.MEDIUM
        assert secret_info.validation_status == ValidationStatus.VALID
        assert secret_info.strength_score == 80
        assert secret_info.metadata == {}  # Default empty dict
    
    def test_validation_result_dataclass(self):
        """Test ValidationResult dataclass"""
        result = ValidationResult(
            total_secrets=10,
            valid_secrets=8,
            invalid_secrets=1,
            missing_secrets=1,
            warning_secrets=0,
            critical_issues=[],
            high_issues=[],
            medium_issues=[],
            low_issues=[],
            secret_details=[],
            database_connections={},
            api_key_validations={},
            overall_status=ValidationStatus.VALID,
            validation_summary={}
        )
        
        assert result.total_secrets == 10
        assert result.valid_secrets == 8
        assert result.overall_status == ValidationStatus.VALID
        assert isinstance(result.secret_details, list)
        assert isinstance(result.database_connections, dict)


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])