"""
Secrets Manager for Testing Framework

This module provides comprehensive secrets and environment validation for the
Phase 1 testing framework, including .env file validation, credential verification,
API key validation, and database connection testing.
"""

import os
import sys
import re
import json
import time
import hashlib
import base64
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime, timedelta
import asyncio
import aiohttp
import psycopg2
import redis
import requests
from urllib.parse import urlparse, parse_qs

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Validation status enumeration"""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    MISSING = "missing"
    EXPIRED = "expired"
    RATE_LIMITED = "rate_limited"
    UNKNOWN = "unknown"


class SecretType(Enum):
    """Secret type enumeration"""
    DATABASE_PASSWORD = "database_password"
    API_KEY = "api_key"
    JWT_SECRET = "jwt_secret"
    OAUTH_SECRET = "oauth_secret"
    ENCRYPTION_KEY = "encryption_key"
    CONNECTION_STRING = "connection_string"
    ACCESS_TOKEN = "access_token"
    WEBHOOK_SECRET = "webhook_secret"
    CERTIFICATE = "certificate"
    PRIVATE_KEY = "private_key"
    UNKNOWN = "unknown"


class SecurityLevel(Enum):
    """Security level enumeration"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class SecretInfo:
    """Information about a secret"""
    name: str
    value: Optional[str]
    secret_type: SecretType
    security_level: SecurityLevel
    is_required: bool = True
    is_sensitive: bool = True
    validation_status: ValidationStatus = ValidationStatus.UNKNOWN
    validation_message: Optional[str] = None
    last_validated: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    strength_score: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DatabaseConnectionInfo:
    """Database connection information"""
    name: str
    host: str
    port: int
    database: str
    username: str
    password: str
    connection_string: Optional[str] = None
    ssl_required: bool = False
    timeout: int = 30


@dataclass
class APIKeyInfo:
    """API key information"""
    name: str
    key: str
    provider: str
    endpoint: Optional[str] = None
    rate_limit: Optional[int] = None
    quota_limit: Optional[int] = None
    expiry_date: Optional[datetime] = None
    scopes: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of secrets validation"""
    total_secrets: int
    valid_secrets: int
    invalid_secrets: int
    missing_secrets: int
    warning_secrets: int
    critical_issues: List[str]
    high_issues: List[str]
    medium_issues: List[str]
    low_issues: List[str]
    secret_details: List[SecretInfo]
    database_connections: Dict[str, ValidationStatus]
    api_key_validations: Dict[str, ValidationStatus]
    overall_status: ValidationStatus
    validation_summary: Dict[str, Any]


class SecretsManager:
    """
    Manages secrets and environment validation for testing framework.
    
    This class handles .env file validation, credential verification,
    API key validation, and database connection testing.
    """
    
    def __init__(self, project_root: Optional[Path] = None, env_files: Optional[List[str]] = None):
        """
        Initialize the SecretsManager.
        
        Args:
            project_root: Path to the project root directory. If None, uses current directory.
            env_files: List of environment file paths. If None, uses default files.
        """
        self.project_root = project_root or Path.cwd()
        self.env_files = env_files or [".env", ".env.example"]
        
        # Configuration
        self.validation_timeout = 30  # seconds
        self.api_validation_enabled = True
        self.database_validation_enabled = True
        
        # Secret patterns and requirements
        self.secret_patterns = {
            SecretType.API_KEY: [
                r'.*API_KEY.*',
                r'.*_KEY$',
                r'.*TOKEN.*'
            ],
            SecretType.DATABASE_PASSWORD: [
                r'.*PASSWORD.*',
                r'.*PASS.*',
                r'.*PWD.*'
            ],
            SecretType.JWT_SECRET: [
                r'.*JWT.*SECRET.*',
                r'.*SECRET.*KEY.*'
            ],
            SecretType.CONNECTION_STRING: [
                r'.*_URL$',
                r'.*CONNECTION.*',
                r'.*DSN.*'
            ]
        }
        
        # Security requirements
        self.password_requirements = {
            'min_length': 8,
            'require_uppercase': True,
            'require_lowercase': True,
            'require_numbers': True,
            'require_symbols': False,
            'max_age_days': 90
        }
        
        # API endpoints for validation
        self.api_validation_endpoints = {
            'ALPHA_VANTAGE_API_KEY': 'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=1min&apikey={}',
            'FINNHUB_API_KEY': 'https://finnhub.io/api/v1/quote?symbol=AAPL&token={}',
            'TWELVE_DATA_API_KEY': 'https://api.twelvedata.com/time_series?symbol=AAPL&interval=1min&apikey={}',
            'POLYGON_API_KEY': 'https://api.polygon.io/v2/aggs/ticker/AAPL/range/1/day/2023-01-01/2023-01-02?apikey={}',
            'BINANCE_API_KEY': 'https://api.binance.com/api/v3/account',
            'NEWS_API_KEY': 'https://newsapi.org/v2/top-headlines?country=us&apiKey={}',
            'BRAVE_SEARCH_API_KEY': 'https://api.search.brave.com/res/v1/web/search?q=test&key={}'
        }
        
        # Load environment variables
        self.env_vars = {}
        self.secrets_info = {}
        self._load_environment_variables()
    
    def _load_environment_variables(self) -> None:
        """Load environment variables from .env files and system environment."""
        # Load from system environment first
        self.env_vars.update(dict(os.environ))
        
        # Load from .env files (override system environment)
        for env_file in self.env_files:
            env_path = self.project_root / env_file
            if env_path.exists():
                self._load_env_file(env_path)
                logger.info(f"Loaded environment variables from {env_file}")
    
    def _load_env_file(self, env_path: Path) -> None:
        """Load environment variables from a specific .env file."""
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse key=value pairs
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        self.env_vars[key] = value
                    else:
                        logger.warning(f"Invalid line format in {env_path}:{line_num}: {line}")
                        
        except Exception as e:
            logger.error(f"Error loading {env_path}: {str(e)}")
    
    def validate_env_file(self, env_file: Optional[str] = None) -> ValidationResult:
        """
        Validate .env file structure and content.
        
        Args:
            env_file: Specific env file to validate. If None, validates all env files.
            
        Returns:
            ValidationResult: Comprehensive validation results
        """
        logger.info("Starting .env file validation...")
        
        # Analyze all environment variables
        secret_details = []
        critical_issues = []
        high_issues = []
        medium_issues = []
        low_issues = []
        
        for key, value in self.env_vars.items():
            secret_info = self._analyze_secret(key, value)
            secret_details.append(secret_info)
            
            # Categorize issues
            if secret_info.validation_status == ValidationStatus.INVALID:
                if secret_info.security_level == SecurityLevel.CRITICAL:
                    critical_issues.append(f"{key}: {secret_info.validation_message}")
                elif secret_info.security_level == SecurityLevel.HIGH:
                    high_issues.append(f"{key}: {secret_info.validation_message}")
                elif secret_info.security_level == SecurityLevel.MEDIUM:
                    medium_issues.append(f"{key}: {secret_info.validation_message}")
                else:
                    low_issues.append(f"{key}: {secret_info.validation_message}")
        
        # Count validation results
        valid_count = sum(1 for s in secret_details if s.validation_status == ValidationStatus.VALID)
        invalid_count = sum(1 for s in secret_details if s.validation_status == ValidationStatus.INVALID)
        missing_count = sum(1 for s in secret_details if s.validation_status == ValidationStatus.MISSING)
        warning_count = sum(1 for s in secret_details if s.validation_status == ValidationStatus.WARNING)
        
        # Determine overall status
        if critical_issues or (invalid_count > 0 and missing_count > 0):
            overall_status = ValidationStatus.INVALID
        elif high_issues or warning_count > 0:
            overall_status = ValidationStatus.WARNING
        else:
            overall_status = ValidationStatus.VALID
        
        # Create validation summary
        validation_summary = {
            'total_variables': len(secret_details),
            'sensitive_variables': sum(1 for s in secret_details if s.is_sensitive),
            'required_variables': sum(1 for s in secret_details if s.is_required),
            'critical_count': len(critical_issues),
            'high_count': len(high_issues),
            'medium_count': len(medium_issues),
            'low_count': len(low_issues),
            'validation_timestamp': datetime.now().isoformat()
        }
        
        return ValidationResult(
            total_secrets=len(secret_details),
            valid_secrets=valid_count,
            invalid_secrets=invalid_count,
            missing_secrets=missing_count,
            warning_secrets=warning_count,
            critical_issues=critical_issues,
            high_issues=high_issues,
            medium_issues=medium_issues,
            low_issues=low_issues,
            secret_details=secret_details,
            database_connections={},
            api_key_validations={},
            overall_status=overall_status,
            validation_summary=validation_summary
        )
    
    def _analyze_secret(self, key: str, value: str) -> SecretInfo:
        """Analyze a single secret/environment variable."""
        # Determine secret type
        secret_type = self._classify_secret_type(key)
        
        # Determine security level
        security_level = self._determine_security_level(key, secret_type)
        
        # Check if required
        is_required = self._is_required_secret(key)
        
        # Check if sensitive
        is_sensitive = self._is_sensitive_secret(key, secret_type)
        
        # Validate the secret
        validation_status, validation_message, strength_score = self._validate_secret_value(
            key, value, secret_type
        )
        
        # Check for expiry
        expiry_date = self._check_secret_expiry(key, value)
        
        return SecretInfo(
            name=key,
            value=value if not is_sensitive else self._mask_secret(value),
            secret_type=secret_type,
            security_level=security_level,
            is_required=is_required,
            is_sensitive=is_sensitive,
            validation_status=validation_status,
            validation_message=validation_message,
            last_validated=datetime.now(),
            expiry_date=expiry_date,
            strength_score=strength_score,
            metadata={
                'length': len(value) if value else 0,
                'has_special_chars': bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', value)) if value else False,
                'has_numbers': bool(re.search(r'\d', value)) if value else False,
                'has_uppercase': bool(re.search(r'[A-Z]', value)) if value else False,
                'has_lowercase': bool(re.search(r'[a-z]', value)) if value else False
            }
        )
    
    def _classify_secret_type(self, key: str) -> SecretType:
        """Classify the type of secret based on the key name."""
        key_upper = key.upper()
        
        # Check specific classifications first
        if 'JWT' in key_upper:
            return SecretType.JWT_SECRET
        elif 'SECRET_KEY' in key_upper:
            return SecretType.JWT_SECRET
        
        # Then check patterns
        for secret_type, patterns in self.secret_patterns.items():
            for pattern in patterns:
                if re.match(pattern, key_upper):
                    return secret_type
        
        # Additional specific classifications
        if 'OAUTH' in key_upper or 'CLIENT_SECRET' in key_upper:
            return SecretType.OAUTH_SECRET
        elif 'CERT' in key_upper or 'CERTIFICATE' in key_upper:
            return SecretType.CERTIFICATE
        elif 'PRIVATE_KEY' in key_upper or 'PRIV_KEY' in key_upper:
            return SecretType.PRIVATE_KEY
        elif 'WEBHOOK' in key_upper:
            return SecretType.WEBHOOK_SECRET
        elif 'ENCRYPTION' in key_upper:
            return SecretType.ENCRYPTION_KEY
        
        return SecretType.UNKNOWN
    
    def _determine_security_level(self, key: str, secret_type: SecretType) -> SecurityLevel:
        """Determine the security level of a secret."""
        key_upper = key.upper()
        
        # Critical security level
        if secret_type in [SecretType.PRIVATE_KEY, SecretType.ENCRYPTION_KEY]:
            return SecurityLevel.CRITICAL
        elif 'SECRET_KEY' in key_upper or 'JWT' in key_upper:
            return SecurityLevel.CRITICAL
        elif 'ROOT' in key_upper or 'ADMIN' in key_upper:
            return SecurityLevel.CRITICAL
        
        # High security level
        elif secret_type in [SecretType.DATABASE_PASSWORD, SecretType.OAUTH_SECRET]:
            return SecurityLevel.HIGH
        elif 'PASSWORD' in key_upper or 'PASS' in key_upper:
            return SecurityLevel.HIGH
        elif 'CLIENT_SECRET' in key_upper:
            return SecurityLevel.HIGH
        
        # Medium security level
        elif secret_type == SecretType.API_KEY:
            return SecurityLevel.MEDIUM
        elif 'TOKEN' in key_upper:
            return SecurityLevel.MEDIUM
        
        # Low security level
        elif secret_type == SecretType.CONNECTION_STRING:
            return SecurityLevel.LOW
        
        return SecurityLevel.INFO
    
    def _is_required_secret(self, key: str) -> bool:
        """Determine if a secret is required."""
        required_secrets = {
            'SECRET_KEY', 'JWT_SECRET_KEY', 'POSTGRES_PASSWORD', 'DATABASE_URL',
            'REDIS_PASSWORD', 'CLICKHOUSE_PASSWORD', 'ALPHA_VANTAGE_API_KEY'
        }
        
        return key in required_secrets or any(req in key for req in ['PASSWORD', 'SECRET_KEY', 'JWT'])
    
    def _is_sensitive_secret(self, key: str, secret_type: SecretType) -> bool:
        """Determine if a secret is sensitive and should be masked."""
        sensitive_types = {
            SecretType.DATABASE_PASSWORD,
            SecretType.API_KEY,
            SecretType.JWT_SECRET,
            SecretType.OAUTH_SECRET,
            SecretType.ENCRYPTION_KEY,
            SecretType.PRIVATE_KEY,
            SecretType.ACCESS_TOKEN,
            SecretType.WEBHOOK_SECRET
        }
        
        return secret_type in sensitive_types or 'PASSWORD' in key.upper() or 'SECRET' in key.upper()
    
    def _validate_secret_value(self, key: str, value: str, secret_type: SecretType) -> Tuple[ValidationStatus, str, Optional[int]]:
        """Validate the value of a secret."""
        if not value or value.strip() == '':
            return ValidationStatus.MISSING, "Secret value is empty", 0
        
        # Check for placeholder values
        placeholder_patterns = [
            r'^your[_-].*',
            r'^dummy[_-].*',
            r'^test[_-].*',
            r'^example[_-].*',
            r'^placeholder.*',
            r'^change[_-].*',
            r'^replace[_-].*'
        ]
        
        for pattern in placeholder_patterns:
            if re.match(pattern, value.lower()):
                return ValidationStatus.INVALID, "Secret contains placeholder value", 10
        
        # Validate based on secret type
        if secret_type == SecretType.DATABASE_PASSWORD:
            return self._validate_password(value)
        elif secret_type == SecretType.JWT_SECRET:
            return self._validate_jwt_secret(value)
        elif secret_type == SecretType.API_KEY:
            return self._validate_api_key(key, value)
        elif secret_type == SecretType.CONNECTION_STRING:
            return self._validate_connection_string(value)
        else:
            # Generic validation
            if len(value) < 8:
                return ValidationStatus.WARNING, "Secret value is too short", 30
            elif len(value) < 16:
                return ValidationStatus.WARNING, "Secret value could be longer", 60
            else:
                return ValidationStatus.VALID, "Secret value appears valid", 80
    
    def _validate_password(self, password: str) -> Tuple[ValidationStatus, str, int]:
        """Validate password strength."""
        score = 0
        issues = []
        
        # Length check
        if len(password) < self.password_requirements['min_length']:
            issues.append(f"Password too short (minimum {self.password_requirements['min_length']} characters)")
        else:
            score += 20
        
        # Character requirements
        if self.password_requirements['require_uppercase'] and not re.search(r'[A-Z]', password):
            issues.append("Password missing uppercase letters")
        else:
            score += 20
        
        if self.password_requirements['require_lowercase'] and not re.search(r'[a-z]', password):
            issues.append("Password missing lowercase letters")
        else:
            score += 20
        
        if self.password_requirements['require_numbers'] and not re.search(r'\d', password):
            issues.append("Password missing numbers")
        else:
            score += 20
        
        if self.password_requirements['require_symbols'] and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            issues.append("Password missing special characters")
        else:
            score += 20
        
        # Determine status
        if issues:
            if score < 20:  # Very weak passwords are invalid
                return ValidationStatus.INVALID, "; ".join(issues), score
            elif score < 60:  # Weak passwords are invalid
                return ValidationStatus.INVALID, "; ".join(issues), score
            else:
                return ValidationStatus.WARNING, "; ".join(issues), score
        else:
            return ValidationStatus.VALID, "Password meets requirements", score
    
    def _validate_jwt_secret(self, secret: str) -> Tuple[ValidationStatus, str, int]:
        """Validate JWT secret strength."""
        if len(secret) < 32:
            return ValidationStatus.INVALID, "JWT secret too short (minimum 32 characters)", 20
        elif len(secret) < 64:
            return ValidationStatus.WARNING, "JWT secret could be longer (recommended 64+ characters)", 60
        else:
            return ValidationStatus.VALID, "JWT secret meets requirements", 90
    
    def _validate_api_key(self, key_name: str, api_key: str) -> Tuple[ValidationStatus, str, int]:
        """Validate API key format and potentially test it."""
        # Basic format validation
        if len(api_key) < 16:
            return ValidationStatus.INVALID, "API key too short", 20
        
        # Check for common API key patterns
        if key_name == 'ALPHA_VANTAGE_API_KEY':
            if not re.match(r'^[A-Z0-9]{16}$', api_key):
                return ValidationStatus.WARNING, "API key format may be incorrect", 40
        elif key_name == 'FINNHUB_API_KEY':
            if not re.match(r'^[a-z0-9]{20}$', api_key):
                return ValidationStatus.WARNING, "API key format may be incorrect", 40
        
        return ValidationStatus.VALID, "API key format appears valid", 70
    
    def _validate_connection_string(self, conn_str: str) -> Tuple[ValidationStatus, str, int]:
        """Validate database connection string format."""
        try:
            parsed = urlparse(conn_str)
            
            if not parsed.scheme:
                return ValidationStatus.INVALID, "Connection string missing scheme", 20
            
            if not parsed.hostname:
                return ValidationStatus.INVALID, "Connection string missing hostname", 30
            
            if not parsed.username:
                return ValidationStatus.WARNING, "Connection string missing username", 50
            
            if not parsed.password:
                return ValidationStatus.WARNING, "Connection string missing password", 60
            
            return ValidationStatus.VALID, "Connection string format is valid", 90
            
        except Exception as e:
            return ValidationStatus.INVALID, f"Invalid connection string format: {str(e)}", 10
    
    def _check_secret_expiry(self, key: str, value: str) -> Optional[datetime]:
        """Check if a secret has an expiry date."""
        # This would be extended with specific logic for different secret types
        # For now, we'll return None (no expiry tracking)
        return None
    
    def _mask_secret(self, value: str) -> str:
        """Mask sensitive secret values for display."""
        if not value:
            return ""
        
        if len(value) <= 8:
            return "*" * len(value)
        else:
            return value[:4] + "*" * (len(value) - 8) + value[-4:]
    
    def validate_database_connections(self) -> Dict[str, ValidationStatus]:
        """
        Validate database connections using credentials from environment.
        
        Returns:
            Dict[str, ValidationStatus]: Database connection validation results
        """
        logger.info("Validating database connections...")
        
        results = {}
        
        # PostgreSQL connection
        postgres_result = self._validate_postgres_connection()
        if postgres_result is not None:
            results['PostgreSQL'] = postgres_result
        
        # Redis connection
        redis_result = self._validate_redis_connection()
        if redis_result is not None:
            results['Redis'] = redis_result
        
        # ClickHouse connection
        clickhouse_result = self._validate_clickhouse_connection()
        if clickhouse_result is not None:
            results['ClickHouse'] = clickhouse_result
        
        return results
    
    def _validate_postgres_connection(self) -> Optional[ValidationStatus]:
        """Validate PostgreSQL database connection."""
        try:
            # Get connection parameters
            host = self.env_vars.get('POSTGRES_HOST', 'localhost')
            port = int(self.env_vars.get('POSTGRES_PORT', 5432))
            database = self.env_vars.get('POSTGRES_DB', 'trading_system')
            user = self.env_vars.get('POSTGRES_USER', 'postgres')
            password = self.env_vars.get('POSTGRES_PASSWORD', '')
            
            if not password:
                logger.warning("PostgreSQL password not found in environment")
                return ValidationStatus.MISSING
            
            # Test connection
            conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                connect_timeout=self.validation_timeout
            )
            
            # Test basic query
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            logger.info(f"PostgreSQL connection successful: {version[0][:50]}...")
            return ValidationStatus.VALID
            
        except psycopg2.OperationalError as e:
            logger.error(f"PostgreSQL connection failed: {str(e)}")
            return ValidationStatus.INVALID
        except Exception as e:
            logger.error(f"PostgreSQL validation error: {str(e)}")
            return ValidationStatus.UNKNOWN
    
    def _validate_redis_connection(self) -> Optional[ValidationStatus]:
        """Validate Redis connection."""
        try:
            # Get connection parameters
            host = self.env_vars.get('REDIS_HOST', 'localhost')
            port = int(self.env_vars.get('REDIS_PORT', 6379))
            password = self.env_vars.get('REDIS_PASSWORD', '')
            db = int(self.env_vars.get('REDIS_DB', 0))
            
            # Test connection
            r = redis.Redis(
                host=host,
                port=port,
                password=password if password else None,
                db=db,
                socket_timeout=self.validation_timeout,
                socket_connect_timeout=self.validation_timeout
            )
            
            # Test ping
            response = r.ping()
            
            if response:
                logger.info("Redis connection successful")
                return ValidationStatus.VALID
            else:
                logger.error("Redis ping failed")
                return ValidationStatus.INVALID
                
        except redis.ConnectionError as e:
            logger.error(f"Redis connection failed: {str(e)}")
            return ValidationStatus.INVALID
        except Exception as e:
            logger.error(f"Redis validation error: {str(e)}")
            return ValidationStatus.UNKNOWN
    
    def _validate_clickhouse_connection(self) -> Optional[ValidationStatus]:
        """Validate ClickHouse connection."""
        try:
            # Get connection parameters
            host = self.env_vars.get('CLICKHOUSE_HOST', 'localhost')
            port = int(self.env_vars.get('CLICKHOUSE_PORT', 8123))
            user = self.env_vars.get('CLICKHOUSE_USER', 'default')
            password = self.env_vars.get('CLICKHOUSE_PASSWORD', '')
            database = self.env_vars.get('CLICKHOUSE_DB', 'default')
            
            # Test HTTP connection
            url = f"http://{host}:{port}/ping"
            
            auth = None
            if user and password:
                auth = (user, password)
            
            response = requests.get(url, auth=auth, timeout=self.validation_timeout)
            
            if response.status_code == 200 and response.text.strip() == "Ok.":
                logger.info("ClickHouse connection successful")
                return ValidationStatus.VALID
            else:
                logger.error(f"ClickHouse ping failed: {response.status_code} - {response.text}")
                return ValidationStatus.INVALID
                
        except requests.RequestException as e:
            logger.error(f"ClickHouse connection failed: {str(e)}")
            return ValidationStatus.INVALID
        except Exception as e:
            logger.error(f"ClickHouse validation error: {str(e)}")
            return ValidationStatus.UNKNOWN
    
    def validate_api_keys(self) -> Dict[str, ValidationStatus]:
        """
        Validate API keys by making test requests to their respective services.
        
        Returns:
            Dict[str, ValidationStatus]: API key validation results
        """
        logger.info("Validating API keys...")
        
        results = {}
        
        if not self.api_validation_enabled:
            logger.info("API key validation is disabled")
            return results
        
        for key_name, endpoint_template in self.api_validation_endpoints.items():
            api_key = self.env_vars.get(key_name)
            
            if not api_key:
                results[key_name] = ValidationStatus.MISSING
                continue
            
            try:
                result = self._validate_single_api_key(key_name, api_key, endpoint_template)
                results[key_name] = result
                
                # Add delay between API calls to avoid rate limiting
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error validating {key_name}: {str(e)}")
                results[key_name] = ValidationStatus.UNKNOWN
        
        return results
    
    def _validate_single_api_key(self, key_name: str, api_key: str, endpoint_template: str) -> ValidationStatus:
        """Validate a single API key."""
        try:
            # Format the endpoint URL
            if '{}' in endpoint_template:
                url = endpoint_template.format(api_key)
            else:
                url = endpoint_template
            
            # Prepare headers
            headers = {'User-Agent': 'TradingSystem/1.0'}
            
            # Special handling for different APIs
            if key_name == 'BINANCE_API_KEY':
                # Binance requires signature for account endpoint
                # For validation, we'll just check if the key format is correct
                if len(api_key) == 64 and all(c in '0123456789ABCDEFabcdef' for c in api_key):
                    return ValidationStatus.VALID
                else:
                    return ValidationStatus.INVALID
            
            # Make the request
            response = requests.get(url, headers=headers, timeout=self.validation_timeout)
            
            # Analyze response
            if response.status_code == 200:
                # Check if response contains valid data
                try:
                    data = response.json()
                    if self._is_valid_api_response(key_name, data):
                        logger.info(f"{key_name} validation successful")
                        return ValidationStatus.VALID
                    else:
                        logger.warning(f"{key_name} returned unexpected response format")
                        return ValidationStatus.WARNING
                except json.JSONDecodeError:
                    # Some APIs return non-JSON responses
                    if response.text and len(response.text) > 0:
                        logger.info(f"{key_name} validation successful (non-JSON response)")
                        return ValidationStatus.VALID
                    else:
                        return ValidationStatus.INVALID
            
            elif response.status_code == 401:
                logger.error(f"{key_name} authentication failed")
                return ValidationStatus.INVALID
            elif response.status_code == 403:
                logger.error(f"{key_name} access forbidden")
                return ValidationStatus.INVALID
            elif response.status_code == 429:
                logger.warning(f"{key_name} rate limited")
                return ValidationStatus.RATE_LIMITED
            else:
                logger.error(f"{key_name} validation failed with status {response.status_code}")
                return ValidationStatus.INVALID
                
        except requests.Timeout:
            logger.error(f"{key_name} validation timed out")
            return ValidationStatus.UNKNOWN
        except requests.RequestException as e:
            logger.error(f"{key_name} validation request failed: {str(e)}")
            return ValidationStatus.UNKNOWN
    
    def _is_valid_api_response(self, key_name: str, data: Any) -> bool:
        """Check if API response contains valid data."""
        if not data:
            return False
        
        # API-specific validation
        if key_name == 'ALPHA_VANTAGE_API_KEY':
            return 'Time Series (1min)' in data or 'Meta Data' in data
        elif key_name == 'FINNHUB_API_KEY':
            return 'c' in data or 'h' in data or 'l' in data  # Current, high, low prices
        elif key_name == 'TWELVE_DATA_API_KEY':
            return 'values' in data or 'meta' in data
        elif key_name == 'POLYGON_API_KEY':
            return 'results' in data
        elif key_name == 'NEWS_API_KEY':
            return 'articles' in data
        elif key_name == 'BRAVE_SEARCH_API_KEY':
            return 'web' in data or 'results' in data
        
        # Generic validation - if we get structured data, it's probably valid
        return isinstance(data, (dict, list))
    
    def comprehensive_secrets_validation(self) -> ValidationResult:
        """
        Perform comprehensive secrets validation including env files, database connections, and API keys.
        
        Returns:
            ValidationResult: Complete validation results
        """
        logger.info("Starting comprehensive secrets validation...")
        
        # Validate .env files
        env_result = self.validate_env_file()
        
        # Validate database connections
        if self.database_validation_enabled:
            db_connections = self.validate_database_connections()
        else:
            db_connections = {}
        
        # Validate API keys
        if self.api_validation_enabled:
            api_validations = self.validate_api_keys()
        else:
            api_validations = {}
        
        # Update the result with database and API validations
        env_result.database_connections = db_connections
        env_result.api_key_validations = api_validations
        
        # Update validation summary
        env_result.validation_summary.update({
            'database_connections_tested': len(db_connections),
            'database_connections_valid': sum(1 for status in db_connections.values() if status == ValidationStatus.VALID),
            'api_keys_tested': len(api_validations),
            'api_keys_valid': sum(1 for status in api_validations.values() if status == ValidationStatus.VALID),
            'comprehensive_validation': True
        })
        
        # Re-evaluate overall status considering database and API validations
        db_failures = sum(1 for status in db_connections.values() if status == ValidationStatus.INVALID)
        api_failures = sum(1 for status in api_validations.values() if status == ValidationStatus.INVALID)
        
        if db_failures > 0 or api_failures > 0:
            if env_result.overall_status == ValidationStatus.VALID:
                env_result.overall_status = ValidationStatus.WARNING
        
        logger.info("Comprehensive secrets validation completed")
        return env_result
    
    def generate_secrets_report(self) -> str:
        """
        Generate a comprehensive secrets validation report.
        
        Returns:
            str: Formatted secrets validation report
        """
        validation_result = self.comprehensive_secrets_validation()
        
        report_lines = [
            "=" * 80,
            "SECRETS VALIDATION REPORT",
            "=" * 80,
            f"Overall Status: {validation_result.overall_status.value.upper()}",
            f"Timestamp: {datetime.now().isoformat()}",
            "",
            "SUMMARY:",
            f"  Total Secrets: {validation_result.total_secrets}",
            f"  Valid: {validation_result.valid_secrets}",
            f"  Invalid: {validation_result.invalid_secrets}",
            f"  Missing: {validation_result.missing_secrets}",
            f"  Warnings: {validation_result.warning_secrets}",
            ""
        ]
        
        # Critical issues
        if validation_result.critical_issues:
            report_lines.extend([
                "🚨 CRITICAL ISSUES:",
                *[f"  - {issue}" for issue in validation_result.critical_issues],
                ""
            ])
        
        # High priority issues
        if validation_result.high_issues:
            report_lines.extend([
                "⚠️ HIGH PRIORITY ISSUES:",
                *[f"  - {issue}" for issue in validation_result.high_issues],
                ""
            ])
        
        # Database connections
        if validation_result.database_connections:
            report_lines.extend([
                "DATABASE CONNECTIONS:",
                *[f"  {db}: {status.value}" for db, status in validation_result.database_connections.items()],
                ""
            ])
        
        # API key validations
        if validation_result.api_key_validations:
            report_lines.extend([
                "API KEY VALIDATIONS:",
                *[f"  {key}: {status.value}" for key, status in validation_result.api_key_validations.items()],
                ""
            ])
        
        # Security recommendations
        report_lines.extend([
            "SECURITY RECOMMENDATIONS:",
            "  - Rotate secrets regularly (every 90 days)",
            "  - Use strong passwords with mixed case, numbers, and symbols",
            "  - Store secrets in secure vaults in production",
            "  - Monitor for secret exposure in logs and code",
            "  - Implement secret scanning in CI/CD pipelines",
            "",
            "VALIDATION SUMMARY:",
            *[f"  {key}: {value}" for key, value in validation_result.validation_summary.items()],
            "=" * 80
        ])
        
        return "\n".join(report_lines)
    
    def get_secret_value(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a secret value by key.
        
        Args:
            key: Secret key name
            default: Default value if key not found
            
        Returns:
            Optional[str]: Secret value or default
        """
        return self.env_vars.get(key, default)
    
    def set_validation_options(self, api_validation: bool = True, database_validation: bool = True) -> None:
        """
        Set validation options.
        
        Args:
            api_validation: Enable API key validation
            database_validation: Enable database connection validation
        """
        self.api_validation_enabled = api_validation
        self.database_validation_enabled = database_validation
        logger.info(f"Validation options updated: API={api_validation}, DB={database_validation}")
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        # Clear sensitive data from memory
        if hasattr(self, 'env_vars'):
            self.env_vars.clear()
        if hasattr(self, 'secrets_info'):
            self.secrets_info.clear()