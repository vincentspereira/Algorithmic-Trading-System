"""
Test suite for advanced REST API system including rate limiting,
API versioning, OpenAPI generation, and comprehensive documentation.
"""
import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import uuid
import tempfile
import os

# Import the modules to test
from nautilus_trader_engine.api.advanced_rest_api import (
    AdvancedRestAPI, RateLimiter, APIKeyManager, APIVersionManager,
    APIKey, RateLimitRule, APIUsageStats, APIVersion as APIVersionEnum,
    RateLimitType, AuthenticationMethod, create_advanced_api
)
from nautilus_trader_engine.api.openapi_generator import (
    OpenAPIGenerator, OpenAPIEndpoint, OpenAPISchema, OpenAPIParameter,
    OpenAPIResponse, ParameterLocation, DataType, create_openapi_generator
)
from nautilus_trader_engine.api.versioning import (
    VersionManager, DataTransformer, VersionedResource, APIVersion,
    VersionCompatibility, FieldMapping, VersioningStrategy, DeprecationLevel,
    create_version_manager, create_data_transformer, versioned_endpoint
)

class TestRateLimiter:
    """Test rate limiting functionality"""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter for testing"""
        return RateLimiter()
    
    def test_rate_limiter_initialization(self, rate_limiter):
        """Test rate limiter initialization"""
        assert rate_limiter.redis_client is None
        assert rate_limiter.memory_store is not None
        assert rate_limiter.logger is not None
    
    def test_memory_rate_limiting_allowed(self, rate_limiter):
        """Test memory-based rate limiting when allowed"""
        rule = RateLimitRule(limit=5, period=60, per="minute")
        key = "test_key"
        
        # First request should be allowed
        allowed, info = rate_limiter.is_allowed(key, rule)
        
        assert allowed is True
        assert info['limit'] == 5
        assert info['remaining'] == 4
        assert info['retry_after'] == 0
    
    def test_memory_rate_limiting_exceeded(self, rate_limiter):
        """Test memory-based rate limiting when exceeded"""
        rule = RateLimitRule(limit=2, period=60, per="minute")
        key = "test_key_exceeded"
        
        # Make requests up to limit
        for i in range(2):
            allowed, info = rate_limiter.is_allowed(key, rule)
            assert allowed is True
        
        # Next request should be denied
        allowed, info = rate_limiter.is_allowed(key, rule)
        
        assert allowed is False
        assert info['limit'] == 2
        assert info['remaining'] == 0
        assert info['retry_after'] > 0
    
    def test_rate_limit_window_expiry(self, rate_limiter):
        """Test rate limit window expiry"""
        rule = RateLimitRule(limit=1, period=1, per="second")  # 1 request per second
        key = "test_key_expiry"
        
        # First request should be allowed
        allowed, info = rate_limiter.is_allowed(key, rule)
        assert allowed is True
        
        # Second request should be denied
        allowed, info = rate_limiter.is_allowed(key, rule)
        assert allowed is False
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Request should be allowed again
        allowed, info = rate_limiter.is_allowed(key, rule)
        assert allowed is True

class TestAPIKeyManager:
    """Test API key management"""
    
    @pytest.fixture
    def api_key_manager(self):
        """Create API key manager for testing"""
        return APIKeyManager()
    
    def test_api_key_manager_initialization(self, api_key_manager):
        """Test API key manager initialization"""
        assert api_key_manager.api_keys == {}
        assert api_key_manager.logger is not None
    
    def test_create_api_key(self, api_key_manager):
        """Test API key creation"""
        user_id = "test_user_123"
        name = "Test API Key"
        permissions = ["read", "write"]
        
        api_key, raw_key = api_key_manager.create_api_key(
            user_id=user_id,
            name=name,
            permissions=permissions
        )
        
        assert api_key.user_id == user_id
        assert api_key.name == name
        assert api_key.permissions == permissions
        assert api_key.is_active is True
        assert api_key.expires_at is None
        assert raw_key is not None
        assert len(raw_key) > 20  # Should be reasonably long
        assert api_key.key_id in api_key_manager.api_keys
    
    def test_create_api_key_with_expiration(self, api_key_manager):
        """Test API key creation with expiration"""
        api_key, raw_key = api_key_manager.create_api_key(
            user_id="test_user",
            name="Expiring Key",
            permissions=["read"],
            expires_hours=24
        )
        
        assert api_key.expires_at is not None
        assert api_key.expires_at > datetime.now()
        assert api_key.expires_at < datetime.now() + timedelta(hours=25)
    
    def test_validate_api_key_valid(self, api_key_manager):
        """Test valid API key validation"""
        api_key, raw_key = api_key_manager.create_api_key(
            user_id="test_user",
            name="Valid Key",
            permissions=["read"]
        )
        
        validated_key = api_key_manager.validate_api_key(raw_key)
        
        assert validated_key is not None
        assert validated_key.key_id == api_key.key_id
        assert validated_key.user_id == api_key.user_id
        assert validated_key.usage_count == 1
        assert validated_key.last_used is not None
    
    def test_validate_api_key_invalid(self, api_key_manager):
        """Test invalid API key validation"""
        invalid_key = "invalid_key_12345"
        
        validated_key = api_key_manager.validate_api_key(invalid_key)
        
        assert validated_key is None
    
    def test_validate_api_key_expired(self, api_key_manager):
        """Test expired API key validation"""
        api_key, raw_key = api_key_manager.create_api_key(
            user_id="test_user",
            name="Expired Key",
            permissions=["read"],
            expires_hours=1
        )
        
        # Manually expire the key
        api_key.expires_at = datetime.now() - timedelta(hours=1)
        
        validated_key = api_key_manager.validate_api_key(raw_key)
        
        assert validated_key is None
    
    def test_revoke_api_key(self, api_key_manager):
        """Test API key revocation"""
        api_key, raw_key = api_key_manager.create_api_key(
            user_id="test_user",
            name="Key to Revoke",
            permissions=["read"]
        )
        
        # Revoke the key
        result = api_key_manager.revoke_api_key(api_key.key_id, "test_user")
        
        assert result is True
        assert api_key.is_active is False
        
        # Validation should fail for revoked key
        validated_key = api_key_manager.validate_api_key(raw_key)
        assert validated_key is None
    
    def test_revoke_api_key_unauthorized(self, api_key_manager):
        """Test unauthorized API key revocation"""
        api_key, raw_key = api_key_manager.create_api_key(
            user_id="test_user",
            name="Protected Key",
            permissions=["read"]
        )
        
        # Try to revoke with different user
        result = api_key_manager.revoke_api_key(api_key.key_id, "different_user")
        
        assert result is False
        assert api_key.is_active is True
    
    def test_list_user_keys(self, api_key_manager):
        """Test listing user's API keys"""
        user_id = "test_user_list"
        
        # Create multiple keys for user
        key1, _ = api_key_manager.create_api_key(user_id, "Key 1", ["read"])
        key2, _ = api_key_manager.create_api_key(user_id, "Key 2", ["write"])
        
        # Create key for different user
        key3, _ = api_key_manager.create_api_key("other_user", "Other Key", ["read"])
        
        user_keys = api_key_manager.list_user_keys(user_id)
        
        assert len(user_keys) == 2
        key_ids = [key.key_id for key in user_keys]
        assert key1.key_id in key_ids
        assert key2.key_id in key_ids
        assert key3.key_id not in key_ids

class TestAPIVersionManager:
    """Test API version management"""
    
    @pytest.fixture
    def version_manager(self):
        """Create API version manager for testing"""
        return APIVersionManager()
    
    def test_version_manager_initialization(self, version_manager):
        """Test version manager initialization"""
        assert len(version_manager.endpoints) == len(APIVersionEnum)
        assert version_manager.default_version == APIVersionEnum.V1
        assert version_manager.logger is not None
    
    def test_register_endpoint(self, version_manager):
        """Test endpoint registration"""
        from nautilus_trader_engine.api.advanced_rest_api import APIEndpoint
        
        endpoint = APIEndpoint(
            path="/test",
            method="GET",
            version=APIVersionEnum.V1,
            handler=lambda: {"test": "data"},
            description="Test endpoint"
        )
        
        version_manager.register_endpoint(endpoint)
        
        retrieved = version_manager.get_endpoint("GET", "/test", APIVersionEnum.V1)
        assert retrieved is not None
        assert retrieved.path == "/test"
        assert retrieved.method == "GET"
        assert retrieved.version == APIVersionEnum.V1
    
    def test_get_endpoint_not_found(self, version_manager):
        """Test getting non-existent endpoint"""
        endpoint = version_manager.get_endpoint("GET", "/nonexistent")
        assert endpoint is None
    
    @patch('nautilus_trader_engine.api.advanced_rest_api.request')
    def test_get_version_from_request_accept_header(self, mock_request, version_manager):
        """Test version extraction from Accept header"""
        mock_request.headers.get.return_value = 'application/vnd.nautilus.v2+json'
        mock_request.path = '/api/test'
        mock_request.args.get.return_value = None
        
        version = version_manager.get_version_from_request(mock_request)
        assert version == APIVersionEnum.V2
    
    @patch('nautilus_trader_engine.api.advanced_rest_api.request')
    def test_get_version_from_request_url_path(self, mock_request, version_manager):
        """Test version extraction from URL path"""
        mock_request.headers.get.return_value = ''
        mock_request.path = '/api/v3/test'
        mock_request.args.get.return_value = None
        
        version = version_manager.get_version_from_request(mock_request)
        assert version == APIVersionEnum.V3
    
    @patch('nautilus_trader_engine.api.advanced_rest_api.request')
    def test_get_version_from_request_query_param(self, mock_request, version_manager):
        """Test version extraction from query parameter"""
        mock_request.headers.get.return_value = ''
        mock_request.path = '/api/test'
        mock_request.args.get.return_value = 'v2'
        
        version = version_manager.get_version_from_request(mock_request)
        assert version == APIVersionEnum.V2
    
    @patch('nautilus_trader_engine.api.advanced_rest_api.request')
    def test_get_version_from_request_default(self, mock_request, version_manager):
        """Test default version when no version specified"""
        mock_request.headers.get.return_value = ''
        mock_request.path = '/api/test'
        mock_request.args.get.return_value = None
        
        version = version_manager.get_version_from_request(mock_request)
        assert version == APIVersionEnum.V1

class TestOpenAPIGenerator:
    """Test OpenAPI specification generation"""
    
    @pytest.fixture
    def openapi_generator(self):
        """Create OpenAPI generator for testing"""
        return create_openapi_generator(
            title="Test API",
            version="1.0.0",
            description="Test API description"
        )
    
    def test_openapi_generator_initialization(self, openapi_generator):
        """Test OpenAPI generator initialization"""
        assert openapi_generator.title == "Test API"
        assert openapi_generator.version == "1.0.0"
        assert openapi_generator.description == "Test API description"
        assert len(openapi_generator.schemas) > 0  # Should have default schemas
        assert len(openapi_generator.security_schemes) > 0  # Should have default security
        assert len(openapi_generator.tags) > 0  # Should have default tags
    
    def test_add_server(self, openapi_generator):
        """Test adding server"""
        openapi_generator.add_server("https://api.example.com", "Production server")
        
        assert len(openapi_generator.servers) == 1
        assert openapi_generator.servers[0]["url"] == "https://api.example.com"
        assert openapi_generator.servers[0]["description"] == "Production server"
    
    def test_add_tag(self, openapi_generator):
        """Test adding tag"""
        initial_count = len(openapi_generator.tags)
        openapi_generator.add_tag("Custom", "Custom operations")
        
        assert len(openapi_generator.tags) == initial_count + 1
        custom_tag = next(tag for tag in openapi_generator.tags if tag["name"] == "Custom")
        assert custom_tag["description"] == "Custom operations"
    
    def test_add_schema(self, openapi_generator):
        """Test adding schema"""
        from nautilus_trader_engine.api.openapi_generator import OpenAPISchema
        
        schema = OpenAPISchema(
            name="TestModel",
            schema_type=DataType.OBJECT,
            properties={
                "id": {"type": "string", "description": "Unique identifier"},
                "name": {"type": "string", "description": "Name field"}
            },
            required=["id", "name"],
            description="Test model schema"
        )
        
        openapi_generator.add_schema(schema)
        
        assert "TestModel" in openapi_generator.schemas
        assert openapi_generator.schemas["TestModel"].name == "TestModel"
        assert openapi_generator.schemas["TestModel"].description == "Test model schema"
    
    def test_add_endpoint(self, openapi_generator):
        """Test adding endpoint"""
        endpoint = OpenAPIEndpoint(
            path="/test/{id}",
            method="GET",
            summary="Get test item",
            description="Retrieve a test item by ID",
            tags=["Test"],
            parameters=[
                OpenAPIParameter(
                    name="id",
                    location=ParameterLocation.PATH,
                    data_type=DataType.STRING,
                    required=True,
                    description="Test item ID"
                )
            ],
            responses=[
                OpenAPIResponse(
                    status_code=200,
                    description="Test item retrieved successfully"
                )
            ]
        )
        
        openapi_generator.add_endpoint(endpoint)
        
        assert len(openapi_generator.endpoints) == 1
        assert openapi_generator.endpoints[0].path == "/test/{id}"
        assert openapi_generator.endpoints[0].method == "GET"
    
    def test_generate_specification(self, openapi_generator):
        """Test generating complete specification"""
        # Add some test data
        openapi_generator.add_server("https://api.test.com", "Test server")
        
        spec = openapi_generator.generate_specification()
        
        assert spec["openapi"] == "3.0.3"
        assert spec["info"]["title"] == "Test API"
        assert spec["info"]["version"] == "1.0.0"
        assert spec["info"]["description"] == "Test API description"
        assert len(spec["servers"]) == 1
        assert "components" in spec
        assert "schemas" in spec["components"]
        assert "securitySchemes" in spec["components"]
        assert "security" in spec
    
    def test_save_specification_json(self, openapi_generator):
        """Test saving specification as JSON"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            openapi_generator.save_specification(temp_path, "json")
            
            # Verify file was created and contains valid JSON
            assert os.path.exists(temp_path)
            with open(temp_path, 'r') as f:
                spec = json.load(f)
                assert spec["openapi"] == "3.0.3"
                assert spec["info"]["title"] == "Test API"
        finally:
            os.unlink(temp_path)
    
    def test_generate_html_documentation(self, openapi_generator):
        """Test generating HTML documentation"""
        html = openapi_generator.generate_html_documentation()
        
        assert isinstance(html, str)
        assert len(html) > 1000  # Should be substantial HTML
        assert "<!DOCTYPE html>" in html
        assert "swagger-ui" in html
        assert "Test API" in html

class TestVersionManager:
    """Test API versioning system"""
    
    @pytest.fixture
    def version_manager(self):
        """Create version manager for testing"""
        return create_version_manager(VersioningStrategy.URL_PATH)
    
    def test_version_manager_initialization(self, version_manager):
        """Test version manager initialization"""
        assert version_manager.default_strategy == VersioningStrategy.URL_PATH
        assert len(version_manager.versions) == 3  # v1, v2, v3
        assert "v1" in version_manager.versions
        assert "v2" in version_manager.versions
        assert "v3" in version_manager.versions
        assert version_manager.versions["v1"].is_default is True
    
    def test_add_version(self, version_manager):
        """Test adding new version"""
        new_version = APIVersion(
            version="v4",
            release_date=datetime(2025, 1, 1),
            changelog=["New features", "Bug fixes"]
        )
        
        version_manager.add_version(new_version)
        
        assert "v4" in version_manager.versions
        assert version_manager.versions["v4"].version == "v4"
        assert len(version_manager.versions["v4"].changelog) == 2
    
    def test_deprecate_version(self, version_manager):
        """Test version deprecation"""
        deprecation_date = datetime.now()
        sunset_date = datetime.now() + timedelta(days=365)
        
        version_manager.deprecate_version(
            "v1",
            deprecation_date=deprecation_date,
            sunset_date=sunset_date,
            level=DeprecationLevel.SOFT
        )
        
        v1 = version_manager.versions["v1"]
        assert v1.deprecation_date == deprecation_date
        assert v1.sunset_date == sunset_date
        assert v1.deprecation_level == DeprecationLevel.SOFT
    
    def test_is_version_supported(self, version_manager):
        """Test version support check"""
        assert version_manager.is_version_supported("v1") is True
        assert version_manager.is_version_supported("v2") is True
        assert version_manager.is_version_supported("v99") is False
        
        # Test sunset version
        version_manager.deprecate_version("v1", level=DeprecationLevel.SUNSET)
        assert version_manager.is_version_supported("v1") is False
    
    def test_get_deprecation_info(self, version_manager):
        """Test getting deprecation information"""
        # Non-deprecated version
        info = version_manager.get_deprecation_info("v2")
        assert info is None
        
        # Deprecated version
        version_manager.deprecate_version("v1", level=DeprecationLevel.SOFT)
        info = version_manager.get_deprecation_info("v1")
        
        assert info is not None
        assert info["version"] == "v1"
        assert info["deprecation_level"] == "soft"
        assert "latest_version" in info
    
    @patch('nautilus_trader_engine.api.versioning.request')
    def test_get_version_from_request_url_path(self, mock_request, version_manager):
        """Test version extraction from URL path"""
        mock_request.path = "/api/v2/test"
        mock_request.args.get.return_value = None
        mock_request.headers.get.return_value = ""
        
        version = version_manager.get_version_from_request(mock_request)
        assert version == "v2"
    
    @patch('nautilus_trader_engine.api.versioning.request')
    def test_get_version_from_request_query_param(self, mock_request, version_manager):
        """Test version extraction from query parameter"""
        version_manager.default_strategy = VersioningStrategy.QUERY_PARAM
        mock_request.path = "/api/test"
        mock_request.args.get.return_value = "v3"
        mock_request.headers.get.return_value = ""
        
        version = version_manager.get_version_from_request(mock_request, VersioningStrategy.QUERY_PARAM)
        assert version == "v3"

class TestDataTransformer:
    """Test data transformation for version compatibility"""
    
    @pytest.fixture
    def version_manager(self):
        """Create version manager for testing"""
        return create_version_manager()
    
    @pytest.fixture
    def data_transformer(self, version_manager):
        """Create data transformer for testing"""
        return create_data_transformer(version_manager)
    
    def test_data_transformer_initialization(self, data_transformer, version_manager):
        """Test data transformer initialization"""
        assert data_transformer.version_manager == version_manager
        assert data_transformer.logger is not None
    
    def test_transform_request_same_version(self, data_transformer):
        """Test request transformation with same version"""
        data = {"field1": "value1", "field2": "value2"}
        
        result = data_transformer.transform_request(data, "v1", "v1")
        
        assert result == data
        assert result is not data  # Should be a copy
    
    def test_transform_request_no_rule(self, data_transformer):
        """Test request transformation without compatibility rule"""
        data = {"field1": "value1", "field2": "value2"}
        
        result = data_transformer.transform_request(data, "v1", "v99")
        
        assert result == data
    
    def test_transform_request_with_mapping(self, data_transformer, version_manager):
        """Test request transformation with field mapping"""
        # Add compatibility rule
        compatibility = VersionCompatibility(
            source_version="v1",
            target_version="v2",
            field_mappings=[
                FieldMapping(
                    old_field="old_name",
                    new_field="new_name",
                    transformer=lambda x: x.upper()
                )
            ]
        )
        version_manager.add_compatibility_rule(compatibility)
        
        data = {"old_name": "test_value", "other_field": "unchanged"}
        
        result = data_transformer.transform_request(data, "v1", "v2")
        
        assert "old_name" not in result
        assert result["new_name"] == "TEST_VALUE"
        assert result["other_field"] == "unchanged"
    
    def test_transform_response_with_reverse_mapping(self, data_transformer, version_manager):
        """Test response transformation with reverse field mapping"""
        # Add compatibility rule
        compatibility = VersionCompatibility(
            source_version="v1",
            target_version="v2",
            field_mappings=[
                FieldMapping(
                    old_field="old_name",
                    new_field="new_name",
                    transformer=lambda x: x.upper(),
                    reverse_transformer=lambda x: x.lower()
                )
            ]
        )
        version_manager.add_compatibility_rule(compatibility)
        
        data = {"new_name": "TEST_VALUE", "other_field": "unchanged"}
        
        result = data_transformer.transform_response(data, "v2", "v1")
        
        assert "new_name" not in result
        assert result["old_name"] == "test_value"
        assert result["other_field"] == "unchanged"

class TestVersionedEndpointDecorator:
    """Test versioned endpoint decorator"""
    
    def test_versioned_endpoint_decorator(self):
        """Test versioned endpoint decorator"""
        @versioned_endpoint(version="v2", deprecated_in="v3", removed_in="v4")
        def test_endpoint():
            """Test endpoint"""
            return {"message": "test"}
        
        assert hasattr(test_endpoint, '__version__')
        assert test_endpoint.__version__ == "v2"
        assert test_endpoint.__deprecated_in__ == "v3"
        assert test_endpoint.__removed_in__ == "v4"
        
        # Test function still works
        result = test_endpoint()
        assert result["message"] == "test"
    
    def test_versioned_endpoint_deprecation_warning(self):
        """Test deprecation warning from versioned endpoint"""
        @versioned_endpoint(version="v1", deprecated_in="v2")
        def deprecated_endpoint():
            return {"message": "deprecated"}
        
        with pytest.warns(DeprecationWarning, match="deprecated since version v2"):
            deprecated_endpoint()

class TestIntegration:
    """Integration tests for advanced REST API system"""
    
    @pytest.fixture
    def mock_flask_app(self):
        """Create mock Flask app for testing"""
        if not FLASK_AVAILABLE:
            pytest.skip("Flask not available")
        
        app = Mock()
        app.config = {}
        return app
    
    def test_advanced_api_creation_without_flask(self):
        """Test advanced API creation without Flask"""
        with patch('nautilus_trader_engine.api.advanced_rest_api.FLASK_AVAILABLE', False):
            with pytest.raises(ImportError, match="Flask and related packages are required"):
                create_advanced_api()
    
    @patch('nautilus_trader_engine.api.advanced_rest_api.FLASK_AVAILABLE', True)
    @patch('nautilus_trader_engine.api.advanced_rest_api.Flask')
    @patch('nautilus_trader_engine.api.advanced_rest_api.Api')
    @patch('nautilus_trader_engine.api.advanced_rest_api.CORS')
    def test_advanced_api_creation_with_flask(self, mock_cors, mock_api, mock_flask):
        """Test advanced API creation with Flask"""
        mock_app = Mock()
        mock_flask.return_value = mock_app
        mock_api_instance = Mock()
        mock_api.return_value = mock_api_instance
        
        api = create_advanced_api()
        
        assert api is not None
        assert api.app == mock_app
        assert api.api == mock_api_instance
        mock_flask.assert_called_once()
        mock_api.assert_called_once()
        mock_cors.assert_called_once()
    
    def test_end_to_end_api_workflow(self):
        """Test complete API workflow"""
        # Create components
        version_manager = create_version_manager()
        data_transformer = create_data_transformer(version_manager)
        openapi_generator = create_openapi_generator()
        
        # Add compatibility rule
        compatibility = VersionCompatibility(
            source_version="v1",
            target_version="v2",
            field_mappings=[
                FieldMapping(
                    old_field="status",
                    new_field="state",
                    transformer=lambda x: x.upper()
                )
            ]
        )
        version_manager.add_compatibility_rule(compatibility)
        
        # Add OpenAPI endpoint
        endpoint = OpenAPIEndpoint(
            path="/orders",
            method="POST",
            summary="Create order",
            description="Create a new trading order",
            tags=["Trading"]
        )
        openapi_generator.add_endpoint(endpoint)
        
        # Test data transformation
        v1_data = {"status": "active", "amount": 100}
        v2_data = data_transformer.transform_request(v1_data, "v1", "v2")
        
        assert v2_data["state"] == "ACTIVE"
        assert v2_data["amount"] == 100
        
        # Test OpenAPI generation
        spec = openapi_generator.generate_specification()
        
        assert "paths" in spec
        assert "/orders" in spec["paths"]
        assert "post" in spec["paths"]["/orders"]
        
        # Verify integration works
        assert len(version_manager.versions) == 3
        assert len(version_manager.compatibility_rules) == 1
        assert len(openapi_generator.endpoints) == 1

if __name__ == "__main__":
    pytest.main([__file__, "-v"])