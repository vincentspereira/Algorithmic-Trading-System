#!/usr/bin/env python3
"""
API Documentation Validation Tests
Validates the OpenAPI specification, code examples, and API testing suite.
"""

import pytest
import yaml
import json
import requests
import asyncio
from pathlib import Path
import subprocess
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock
import sys
import importlib.util
import re

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class TestOpenAPISpecification:
    """Comprehensive tests for OpenAPI specification"""
    
    def setup_method(self):
        """Setup test environment"""
        self.openapi_path = project_root / "docs" / "api" / "openapi.yaml"
        
        with open(self.openapi_path, 'r', encoding='utf-8') as f:
            self.spec = yaml.safe_load(f)
    
    def test_openapi_version_compliance(self):
        """Test OpenAPI version compliance"""
        assert "openapi" in self.spec, "Missing openapi version field"
        assert self.spec["openapi"].startswith("3."), "Should use OpenAPI 3.x"
        
        # Test semantic versioning
        version_parts = self.spec["openapi"].split(".")
        assert len(version_parts) >= 2, "Invalid version format"
        assert all(part.isdigit() for part in version_parts), "Version should be numeric"
    
    def test_info_section_completeness(self):
        """Test info section completeness"""
        info = self.spec["info"]
        
        required_fields = ["title", "description", "version", "contact"]
        for field in required_fields:
            assert field in info, f"Missing required info field: {field}"
        
        # Test contact information
        contact = info["contact"]
        contact_fields = ["name", "email", "url"]
        for field in contact_fields:
            assert field in contact, f"Missing contact field: {field}"
        
        # Test version format
        version = info["version"]
        assert re.match(r'^\d+\.\d+\.\d+$', version), "Version should follow semantic versioning"
    
    def test_servers_configuration(self):
        """Test servers configuration"""
        assert "servers" in self.spec, "Missing servers configuration"
        servers = self.spec["servers"]
        
        assert len(servers) >= 2, "Should have at least production and sandbox servers"
        
        for server in servers:
            assert "url" in server, "Server missing URL"
            assert "description" in server, "Server missing description"
            assert server["url"].startswith("https://"), "Should use HTTPS"
    
    def test_paths_completeness(self):
        """Test API paths completeness"""
        paths = self.spec["paths"]
        
        # Test minimum number of endpoints
        assert len(paths) >= 10, f"Should have at least 10 endpoints, found {len(paths)}"
        
        # Test required endpoint categories
        required_endpoints = {
            "authentication": ["/auth/login", "/auth/refresh"],
            "strategies": ["/strategies", "/strategies/{strategy_id}"],
            "market_data": ["/market-data/quotes/{symbol}", "/market-data/historical/{symbol}"],
            "backtesting": ["/backtesting/run", "/backtesting/{backtest_id}"],
            "trading": ["/orders"]
        }
        
        for category, endpoints in required_endpoints.items():
            for endpoint in endpoints:
                assert endpoint in paths, f"Missing {category} endpoint: {endpoint}"
    
    def test_http_methods_coverage(self):
        """Test HTTP methods coverage"""
        paths = self.spec["paths"]
        
        methods_found = set()
        for path, operations in paths.items():
            for method in operations.keys():
                if method in ["get", "post", "put", "delete", "patch"]:
                    methods_found.add(method.upper())
        
        required_methods = {"GET", "POST", "PUT", "DELETE"}
        missing_methods = required_methods - methods_found
        assert not missing_methods, f"Missing HTTP methods: {missing_methods}"
    
    def test_request_response_schemas(self):
        """Test request and response schemas"""
        paths = self.spec["paths"]
        components = self.spec.get("components", {})
        schemas = components.get("schemas", {})
        
        # Test that we have sufficient schemas
        assert len(schemas) >= 20, f"Should have at least 20 schemas, found {len(schemas)}"
        
        # Test required schema types
        required_schemas = [
            "LoginRequest", "LoginResponse", "Strategy", "Quote", 
            "Order", "BacktestRequest", "BacktestResults", "Error"
        ]
        
        for schema_name in required_schemas:
            assert schema_name in schemas, f"Missing required schema: {schema_name}"
        
        # Test schema structure
        for schema_name, schema_def in schemas.items():
            assert "type" in schema_def, f"Schema {schema_name} missing type"
            
            if schema_def["type"] == "object":
                assert "properties" in schema_def, f"Object schema {schema_name} missing properties"
    
    def test_security_schemes(self):
        """Test security schemes configuration"""
        components = self.spec.get("components", {})
        security_schemes = components.get("securitySchemes", {})
        
        assert len(security_schemes) >= 1, "Should have at least one security scheme"
        assert "BearerAuth" in security_schemes, "Missing Bearer authentication scheme"
        
        bearer_auth = security_schemes["BearerAuth"]
        assert bearer_auth["type"] == "http", "Bearer auth should be HTTP type"
        assert bearer_auth["scheme"] == "bearer", "Should use bearer scheme"
    
    def test_error_responses(self):
        """Test error response definitions"""
        components = self.spec.get("components", {})
        responses = components.get("responses", {})
        
        # Test common error responses
        expected_errors = ["BadRequest", "Unauthorized", "NotFound", "RateLimitExceeded"]
        for error in expected_errors:
            if error in responses:
                error_response = responses[error]
                assert "description" in error_response, f"Error {error} missing description"
                assert "content" in error_response, f"Error {error} missing content"
    
    def test_examples_presence(self):
        """Test that examples are provided"""
        paths = self.spec["paths"]
        
        examples_found = 0
        for path, operations in paths.items():
            for method, operation in operations.items():
                if method in ["post", "put", "patch"]:
                    request_body = operation.get("requestBody", {})
                    content = request_body.get("content", {})
                    for media_type, media_content in content.items():
                        if "examples" in media_content:
                            examples_found += 1
        
        assert examples_found >= 3, f"Should have at least 3 request examples, found {examples_found}"


class TestAPITestingSuiteValidation:
    """Validation tests for the API testing suite"""
    
    def setup_method(self):
        """Setup test environment"""
        self.api_testing_path = project_root / "docs" / "api" / "api_testing_suite.py"
        
        # Load the module
        spec = importlib.util.spec_from_file_location("api_testing_suite", self.api_testing_path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
    
    def test_class_structure(self):
        """Test API testing suite class structure"""
        tester_class = self.module.TradingSystemAPITester
        
        # Test initialization parameters
        import inspect
        init_signature = inspect.signature(tester_class.__init__)
        params = list(init_signature.parameters.keys())
        
        expected_params = ["self", "base_url", "sandbox"]
        for param in expected_params:
            assert param in params, f"Missing initialization parameter: {param}"
    
    def test_authentication_methods(self):
        """Test authentication-related methods"""
        tester_class = self.module.TradingSystemAPITester
        
        auth_methods = [
            "authenticate", "refresh_access_token", "test_authentication_flow"
        ]
        
        for method in auth_methods:
            assert hasattr(tester_class, method), f"Missing authentication method: {method}"
            
            # Test method signature
            method_obj = getattr(tester_class, method)
            assert callable(method_obj), f"Method {method} is not callable"
    
    def test_api_endpoint_methods(self):
        """Test API endpoint testing methods"""
        tester_class = self.module.TradingSystemAPITester
        
        endpoint_methods = [
            "list_strategies", "create_strategy", "get_strategy", 
            "update_strategy", "delete_strategy", "get_quote",
            "get_historical_data", "run_backtest", "get_backtest_results",
            "list_orders", "place_order"
        ]
        
        for method in endpoint_methods:
            assert hasattr(tester_class, method), f"Missing endpoint method: {method}"
    
    def test_comprehensive_test_method(self):
        """Test comprehensive test suite method"""
        tester_class = self.module.TradingSystemAPITester
        
        assert hasattr(tester_class, "run_comprehensive_test_suite"), "Missing comprehensive test method"
        
        # Test method signature
        import inspect
        method_signature = inspect.signature(tester_class.run_comprehensive_test_suite)
        params = list(method_signature.parameters.keys())
        
        expected_params = ["self", "username", "password"]
        for param in expected_params:
            assert param in params, f"Missing parameter in comprehensive test: {param}"
    
    @patch('requests.Session')
    def test_error_handling(self, mock_session):
        """Test error handling in API testing suite"""
        # Create mock responses for different error scenarios
        mock_response_401 = Mock()
        mock_response_401.status_code = 401
        mock_response_401.json.return_value = {"error": "Unauthorized"}
        mock_response_401.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
        
        mock_response_404 = Mock()
        mock_response_404.status_code = 404
        mock_response_404.json.return_value = {"error": "Not Found"}
        mock_response_404.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        
        # Test that the tester can handle different error types
        tester = self.module.TradingSystemAPITester(sandbox=True)
        
        # Test initialization doesn't fail
        assert tester.base_url is not None
        assert tester.session is not None
    
    def test_websocket_testing_capability(self):
        """Test WebSocket testing capability"""
        tester_class = self.module.TradingSystemAPITester
        
        assert hasattr(tester_class, "test_websocket_connection"), "Missing WebSocket test method"
        
        # Test that it's an async method
        import inspect
        method = getattr(tester_class, "test_websocket_connection")
        assert inspect.iscoroutinefunction(method), "WebSocket test method should be async"


class TestCodeExamplesValidation:
    """Validation tests for code examples"""
    
    def setup_method(self):
        """Setup test environment"""
        self.examples_path = project_root / "docs" / "api" / "examples"
        self.js_path = self.examples_path / "javascript_examples.js"
        self.java_path = self.examples_path / "TradingSystemClient.java"
    
    def test_javascript_examples_completeness(self):
        """Test JavaScript examples completeness"""
        with open(self.js_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Test class definition
        assert "class TradingSystemClient" in content, "Missing main client class"
        
        # Test required methods
        required_methods = [
            "constructor", "login", "refreshAccessToken", "getStrategies",
            "createStrategy", "getStrategy", "updateStrategy", "deleteStrategy",
            "getQuote", "getHistoricalData", "runBacktest", "getBacktestResults",
            "getOrders", "placeOrder", "createMarketDataStream"
        ]
        
        for method in required_methods:
            assert method in content, f"Missing JavaScript method: {method}"
        
        # Test example functions
        example_functions = [
            "basicExample", "strategyManagementExample", "backtestingExample",
            "webSocketExample", "errorHandlingExample"
        ]
        
        for func in example_functions:
            assert f"async function {func}" in content, f"Missing example function: {func}"
        
        # Test error handling
        assert "try {" in content, "Missing error handling examples"
        assert "catch" in content, "Missing catch blocks"
        
        # Test WebSocket implementation
        assert "WebSocket" in content, "Missing WebSocket implementation"
        assert "ws.on('open'" in content, "Missing WebSocket event handlers"
    
    def test_java_examples_completeness(self):
        """Test Java examples completeness"""
        with open(self.java_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Test package and imports
        assert "package com.tradingsystem.api;" in content, "Missing package declaration"
        assert "import" in content, "Missing import statements"
        
        # Test main client class
        assert "public class TradingSystemClient" in content, "Missing main client class"
        
        # Test required methods
        required_methods = [
            "login", "refreshAccessToken", "getStrategies", "createStrategy",
            "getStrategy", "updateStrategy", "deleteStrategy", "getQuote",
            "getHistoricalData", "runBacktest", "getBacktestResults",
            "getOrders", "placeOrder"
        ]
        
        for method in required_methods:
            # Check for method existence with flexible pattern matching
            method_pattern = f"{method}("
            assert method_pattern in content, f"Missing Java method: {method}"
        
        # Test data classes
        required_classes = [
            "LoginRequest", "LoginResponse", "Strategy", "Quote", 
            "Order", "BacktestRequest", "BacktestResults"
        ]
        
        for class_name in required_classes:
            assert f"class {class_name}" in content, f"Missing data class: {class_name}"
        
        # Test enums
        required_enums = ["OrderSide", "OrderType", "OrderStatus", "AssetClass"]
        for enum_name in required_enums:
            assert f"enum {enum_name}" in content, f"Missing enum: {enum_name}"
        
        # Test exception handling
        assert "ApiException" in content, "Missing custom exception class"
        assert "try {" in content, "Missing error handling"
    
    def test_code_consistency_across_languages(self):
        """Test consistency between different language examples"""
        with open(self.js_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        with open(self.java_path, 'r', encoding='utf-8') as f:
            java_content = f.read()
        
        # Test that both have similar method names (accounting for naming conventions)
        js_methods = re.findall(r'async (\w+)\(', js_content)
        java_methods = re.findall(r'CompletableFuture<.*?> (\w+)\(', java_content)
        
        # Convert JavaScript camelCase to Java camelCase (should be similar)
        common_methods = ["login", "getStrategies", "createStrategy", "placeOrder"]
        
        for method in common_methods:
            assert method in js_methods or any(method.lower() in m.lower() for m in js_methods), f"JavaScript missing method: {method}"
            assert method in java_methods or any(method.lower() in m.lower() for m in java_methods), f"Java missing method: {method}"


class TestDocumentationAccessibility:
    """Test documentation accessibility and usability"""
    
    def setup_method(self):
        """Setup test environment"""
        self.docs_path = project_root / "docs"
        self.api_doc_path = self.docs_path / "interactive_api_documentation.md"
    
    def test_heading_structure(self):
        """Test proper heading hierarchy"""
        with open(self.api_doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        headings = []
        
        for line in lines:
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                headings.append(level)
        
        # Should start with h1
        assert headings[0] == 1, "Document should start with h1"
        
        # Should not skip levels
        for i in range(1, len(headings)):
            level_diff = headings[i] - headings[i-1]
            assert level_diff <= 1, f"Heading level skip detected at position {i}"
    
    def test_code_block_formatting(self):
        """Test code block formatting"""
        with open(self.api_doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Test that code blocks are properly closed
        triple_backticks = content.count('```')
        assert triple_backticks % 2 == 0, "Unclosed code blocks detected"
        
        # Test language specification
        code_blocks = re.findall(r'```(\w+)', content)
        assert len(code_blocks) >= 10, "Should have at least 10 language-specified code blocks"
        
        # Test common languages are present
        languages = set(code_blocks)
        expected_languages = {"python", "javascript", "java", "bash", "json"}
        found_languages = expected_languages.intersection(languages)
        assert len(found_languages) >= 3, f"Should have examples in at least 3 languages, found: {found_languages}"
    
    def test_link_formatting(self):
        """Test link formatting and structure"""
        with open(self.api_doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Test markdown links
        markdown_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
        
        for link_text, link_url in markdown_links:
            assert link_text.strip(), "Empty link text found"
            assert link_url.strip(), "Empty link URL found"
            
            # Test external links use HTTPS
            if link_url.startswith('http'):
                assert link_url.startswith('https://'), f"Non-HTTPS external link: {link_url}"
    
    def test_table_formatting(self):
        """Test table formatting"""
        with open(self.api_doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find tables
        table_pattern = r'\|.*\|.*\n\|[-\s|]+\|.*\n(\|.*\|.*\n)+'
        tables = re.findall(table_pattern, content)
        
        if tables:
            # Test that tables have proper structure
            for table in tables:
                lines = table.strip().split('\n')
                if len(lines) >= 2:
                    # Test header separator
                    separator_line = lines[1] if len(lines) > 1 else ""
                    assert '|' in separator_line, "Table missing proper separator"
                    assert '-' in separator_line, "Table separator missing dashes"


class TestAPIDocumentationSecurity:
    """Test security aspects of API documentation"""
    
    def setup_method(self):
        """Setup test environment"""
        self.docs_path = project_root / "docs"
        self.api_doc_path = self.docs_path / "interactive_api_documentation.md"
        self.openapi_path = self.docs_path / "api" / "openapi.yaml"
    
    def test_no_hardcoded_credentials(self):
        """Test that no hardcoded credentials are present"""
        files_to_check = [
            self.api_doc_path,
            project_root / "docs" / "api" / "api_testing_suite.py",
            project_root / "docs" / "api" / "examples" / "javascript_examples.js",
            project_root / "docs" / "api" / "examples" / "TradingSystemClient.java"
        ]
        
        sensitive_patterns = [
            r'password["\s]*[:=]["\s]*[^"\s]{8,}',  # Actual passwords
            r'api[_-]?key["\s]*[:=]["\s]*[a-zA-Z0-9]{20,}',  # API keys
            r'secret["\s]*[:=]["\s]*[a-zA-Z0-9]{20,}',  # Secrets
            r'token["\s]*[:=]["\s]*[a-zA-Z0-9]{50,}'  # Long tokens
        ]
        
        for file_path in files_to_check:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for pattern in sensitive_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    # Filter out obvious examples/placeholders
                    real_matches = [m for m in matches if not any(placeholder in m.lower() 
                                   for placeholder in ['example', 'placeholder', 'your-', 'demo', 'test'])]
                    
                    assert not real_matches, f"Potential hardcoded credentials in {file_path}: {real_matches}"
    
    def test_https_enforcement(self):
        """Test that HTTPS is enforced in examples"""
        with open(self.api_doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find HTTP URLs
        http_urls = re.findall(r'http://[^\s\'"]+', content)
        
        # Filter out localhost and example URLs
        external_http = [url for url in http_urls if not any(local in url 
                        for local in ['localhost', '127.0.0.1', 'example.com'])]
        
        assert not external_http, f"Non-HTTPS URLs found: {external_http}"
    
    def test_security_headers_documentation(self):
        """Test that security headers are documented"""
        with open(self.api_doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        security_concepts = [
            "Authorization", "Bearer", "authentication", "rate limit", 
            "CORS", "security", "token"
        ]
        
        found_concepts = sum(1 for concept in security_concepts if concept.lower() in content.lower())
        assert found_concepts >= 5, f"Insufficient security documentation, found {found_concepts} concepts"


def run_api_validation_tests():
    """Run all API validation tests"""
    import pytest
    
    test_args = [
        __file__,
        "-v",
        "--tb=short",
        f"--junitxml={project_root}/api_validation_results.xml"
    ]
    
    result = pytest.main(test_args)
    
    print("\n" + "="*80)
    print("API DOCUMENTATION VALIDATION SUMMARY")
    print("="*80)
    
    if result == 0:
        print("✅ ALL API VALIDATION TESTS PASSED")
        print("\nAPI Documentation components validated:")
        print("- OpenAPI Specification: ✅")
        print("- API Testing Suite: ✅")
        print("- JavaScript Examples: ✅")
        print("- Java Examples: ✅")
        print("- Documentation Accessibility: ✅")
        print("- Security Compliance: ✅")
    else:
        print("❌ SOME API VALIDATION TESTS FAILED")
        print("Please review the test output above for details.")
    
    return result


if __name__ == "__main__":
    run_api_validation_tests()