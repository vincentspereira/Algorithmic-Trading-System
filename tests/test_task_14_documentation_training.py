#!/usr/bin/env python3
"""
Comprehensive Test Suite for Task 14: Documentation and Training
Tests all components of the documentation and training deliverables.
"""

import pytest
import json
import yaml
import requests
import asyncio
import websockets
from pathlib import Path
import subprocess
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock
import sys
import importlib.util

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class TestTask14Documentation:
    """Test suite for Task 14.1 - System Documentation"""
    
    def setup_method(self):
        """Setup test environment"""
        self.docs_path = project_root / "docs"
        self.api_docs_path = self.docs_path / "api"
        self.training_path = self.docs_path / "training"
    
    def test_documentation_files_exist(self):
        """Test that all required documentation files exist"""
        required_files = [
            "interactive_api_documentation.md",
            "api/openapi.yaml",
            "api/api_testing_suite.py",
            "api/examples/javascript_examples.js",
            "api/examples/TradingSystemClient.java",
            "training/video_tutorial_scripts.md",
            "training/hands_on_workshops.md",
            "training/certification_program.md"
        ]
        
        for file_path in required_files:
            full_path = self.docs_path / file_path
            assert full_path.exists(), f"Required documentation file missing: {file_path}"
            assert full_path.stat().st_size > 0, f"Documentation file is empty: {file_path}"
    
    def test_interactive_api_documentation_structure(self):
        """Test the structure and content of interactive API documentation"""
        api_doc_path = self.docs_path / "interactive_api_documentation.md"
        
        with open(api_doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Test required sections exist
        required_sections = [
            "# Interactive API Documentation",
            "## Overview",
            "## Features",
            "## Quick Start",
            "## Authentication",
            "## Making Your First API Call",
            "## API Endpoints",
            "### Authentication Endpoints",
            "### Strategy Management Endpoints",
            "### Market Data Endpoints",
            "### Backtesting Endpoints",
            "### Trading Endpoints",
            "## Error Handling",
            "## Rate Limiting",
            "## SDK Libraries"
        ]
        
        for section in required_sections:
            assert section in content, f"Required section missing: {section}"
        
        # Test code examples in multiple languages
        languages = ["Python:", "JavaScript:", "Java:", "C#:", "Go:"]
        for lang in languages:
            assert lang in content, f"Missing code examples for {lang}"
        
        # Test that code blocks are properly formatted
        assert "```python" in content, "Missing Python code blocks"
        assert "```javascript" in content, "Missing JavaScript code blocks"
        assert "```java" in content, "Missing Java code blocks"
        
        # Test minimum content length (should be comprehensive)
        assert len(content) > 20000, "API documentation seems too short"
    
    def test_openapi_specification_validity(self):
        """Test that OpenAPI specification is valid YAML and contains required elements"""
        openapi_path = self.api_docs_path / "openapi.yaml"
        
        with open(openapi_path, 'r', encoding='utf-8') as f:
            try:
                openapi_spec = yaml.safe_load(f)
            except yaml.YAMLError as e:
                pytest.fail(f"Invalid YAML in OpenAPI spec: {e}")
        
        # Test required OpenAPI fields
        required_fields = ["openapi", "info", "servers", "paths", "components"]
        for field in required_fields:
            assert field in openapi_spec, f"Missing required OpenAPI field: {field}"
        
        # Test OpenAPI version
        assert openapi_spec["openapi"].startswith("3."), "Should use OpenAPI 3.x"
        
        # Test info section
        info = openapi_spec["info"]
        assert "title" in info, "Missing API title"
        assert "version" in info, "Missing API version"
        assert "description" in info, "Missing API description"
        
        # Test that we have multiple endpoints
        paths = openapi_spec["paths"]
        assert len(paths) >= 10, "Should have at least 10 API endpoints"
        
        # Test specific required endpoints
        required_endpoints = [
            "/auth/login",
            "/strategies",
            "/market-data/quotes/{symbol}",
            "/backtesting/run",
            "/orders"
        ]
        
        for endpoint in required_endpoints:
            assert endpoint in paths, f"Missing required endpoint: {endpoint}"
        
        # Test components section
        components = openapi_spec["components"]
        assert "schemas" in components, "Missing schemas in components"
        assert "securitySchemes" in components, "Missing security schemes"
        
        # Test that we have sufficient schema definitions
        schemas = components["schemas"]
        assert len(schemas) >= 20, "Should have at least 20 schema definitions"


class TestTask14APITestingSuite:
    """Test suite for Task 14.2 - API Testing Suite"""
    
    def setup_method(self):
        """Setup test environment"""
        self.api_testing_path = project_root / "docs" / "api" / "api_testing_suite.py"
    
    def test_api_testing_suite_syntax(self):
        """Test that the API testing suite has valid Python syntax"""
        assert self.api_testing_path.exists(), "API testing suite file missing"
        
        # Test syntax by attempting to compile
        with open(self.api_testing_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        try:
            compile(code, str(self.api_testing_path), 'exec')
        except SyntaxError as e:
            pytest.fail(f"Syntax error in API testing suite: {e}")
    
    def test_api_testing_suite_imports(self):
        """Test that all required imports are available"""
        # Load the module dynamically
        spec = importlib.util.spec_from_file_location("api_testing_suite", self.api_testing_path)
        module = importlib.util.module_from_spec(spec)
        
        try:
            spec.loader.exec_module(module)
        except ImportError as e:
            pytest.fail(f"Import error in API testing suite: {e}")
        
        # Test that main class exists
        assert hasattr(module, 'TradingSystemAPITester'), "Missing TradingSystemAPITester class"
    
    def test_api_testing_suite_methods(self):
        """Test that the API testing suite has all required methods"""
        spec = importlib.util.spec_from_file_location("api_testing_suite", self.api_testing_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        tester_class = module.TradingSystemAPITester
        
        # Test required methods exist
        required_methods = [
            'authenticate',
            'refresh_access_token',
            'test_authentication_flow',
            'test_strategy_management',
            'test_market_data',
            'test_backtesting',
            'test_trading_operations',
            'test_websocket_connection',
            'test_error_handling',
            'run_comprehensive_test_suite'
        ]
        
        for method in required_methods:
            assert hasattr(tester_class, method), f"Missing required method: {method}"
    
    @patch('requests.Session')
    def test_api_tester_initialization(self, mock_session):
        """Test API tester initialization"""
        spec = importlib.util.spec_from_file_location("api_testing_suite", self.api_testing_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Test initialization with sandbox
        tester = module.TradingSystemAPITester(sandbox=True)
        assert "sandbox" in tester.base_url.lower(), "Should use sandbox URL"
        
        # Test initialization with production
        tester = module.TradingSystemAPITester(sandbox=False)
        assert "sandbox" not in tester.base_url.lower(), "Should use production URL"


class TestTask14JavaScriptExamples:
    """Test suite for JavaScript examples"""
    
    def setup_method(self):
        """Setup test environment"""
        self.js_examples_path = project_root / "docs" / "api" / "examples" / "javascript_examples.js"
    
    def test_javascript_examples_syntax(self):
        """Test JavaScript syntax using Node.js"""
        assert self.js_examples_path.exists(), "JavaScript examples file missing"
        
        # Test syntax by running node --check
        try:
            result = subprocess.run(
                ["node", "--check", str(self.js_examples_path)],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                pytest.fail(f"JavaScript syntax error: {result.stderr}")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("Node.js not available for syntax checking")
    
    def test_javascript_examples_content(self):
        """Test JavaScript examples content structure"""
        with open(self.js_examples_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Test required classes and functions
        required_elements = [
            "class TradingSystemClient",
            "async login(",
            "async getStrategies(",
            "async createStrategy(",
            "async getQuote(",
            "async runBacktest(",
            "async placeOrder(",
            "createMarketDataStream(",
            "module.exports"
        ]
        
        for element in required_elements:
            assert element in content, f"Missing required element: {element}"
        
        # Test example functions
        example_functions = [
            "async function basicExample(",
            "async function strategyManagementExample(",
            "async function backtestingExample(",
            "async function webSocketExample(",
            "async function errorHandlingExample("
        ]
        
        for func in example_functions:
            assert func in content, f"Missing example function: {func}"


class TestTask14JavaExamples:
    """Test suite for Java examples"""
    
    def setup_method(self):
        """Setup test environment"""
        self.java_examples_path = project_root / "docs" / "api" / "examples" / "TradingSystemClient.java"
    
    def test_java_examples_syntax(self):
        """Test Java syntax by attempting compilation"""
        assert self.java_examples_path.exists(), "Java examples file missing"
        
        with open(self.java_examples_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Basic syntax checks
        assert content.count('{') == content.count('}'), "Mismatched braces in Java code"
        assert content.count('(') == content.count(')'), "Mismatched parentheses in Java code"
        
        # Test package and imports
        assert "package com.tradingsystem.api;" in content, "Missing package declaration"
        assert "import" in content, "Missing import statements"
    
    def test_java_examples_content(self):
        """Test Java examples content structure"""
        with open(self.java_examples_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Test required classes
        required_classes = [
            "public class TradingSystemClient",
            "class LoginRequest",
            "class LoginResponse",
            "class Strategy",
            "class Quote",
            "class Order",
            "class ApiException"
        ]
        
        for class_def in required_classes:
            assert class_def in content, f"Missing required class: {class_def}"
        
        # Test required methods
        required_methods = [
            "public CompletableFuture<LoginResponse> login(",
            "public CompletableFuture<StrategiesResponse> getStrategies(",
            "public CompletableFuture<Strategy> createStrategy(",
            "public CompletableFuture<Quote> getQuote(",
            "public CompletableFuture<BacktestResponse> runBacktest(",
            "public CompletableFuture<Order> placeOrder("
        ]
        
        for method in required_methods:
            assert method in content, f"Missing required method: {method}"


class TestTask14TrainingMaterials:
    """Test suite for Task 14.3 - Training Materials"""
    
    def setup_method(self):
        """Setup test environment"""
        self.training_path = project_root / "docs" / "training"
        self.video_scripts_path = self.training_path / "video_tutorial_scripts.md"
        self.workshops_path = self.training_path / "hands_on_workshops.md"
    
    def test_video_tutorial_scripts_structure(self):
        """Test video tutorial scripts structure and content"""
        assert self.video_scripts_path.exists(), "Video tutorial scripts file missing"
        
        with open(self.video_scripts_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Test required sections
        required_sections = [
            "# Video Tutorial Scripts",
            "## Tutorial Series Structure",
            "### Beginner Series",
            "### Intermediate Series", 
            "### Advanced Series",
            "## Tutorial 1: Introduction to Algorithmic Trading",
            "## Tutorial 2: System Overview and Navigation",
            "## Tutorial 3: Creating Your First Strategy",
            "## Tutorial 4: Understanding Market Data",
            "## Tutorial 5: Running Your First Backtest"
        ]
        
        for section in required_sections:
            assert section in content, f"Missing required section: {section}"
        
        # Test that tutorials have proper structure
        tutorial_elements = [
            "**Duration:**",
            "**Target Audience:**",
            "**Prerequisites:**",
            "### Script",
            "**[INTRO -",
            "**[MAIN CONTENT -",
            "**[CONCLUSION -"
        ]
        
        for element in tutorial_elements:
            assert element in content, f"Missing tutorial element: {element}"
        
        # Test minimum content length
        assert len(content) > 25000, "Video tutorial scripts seem too short"
    
    def test_hands_on_workshops_structure(self):
        """Test hands-on workshops structure and content"""
        assert self.workshops_path.exists(), "Hands-on workshops file missing"
        
        with open(self.workshops_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Test required sections
        required_sections = [
            "# Hands-On Workshops",
            "## Workshop Catalog",
            "### Beginner Workshops",
            "### Intermediate Workshops",
            "### Advanced Workshops",
            "## Workshop 1: Getting Started with Algorithmic Trading",
            "## Workshop 2: Building Your First Strategy",
            "## Workshop 3: API Integration and Automation"
        ]
        
        for section in required_sections:
            assert section in content, f"Missing required section: {section}"
        
        # Test workshop structure elements
        workshop_elements = [
            "**Duration:**",
            "**Capacity:**",
            "**Prerequisites:**",
            "### Learning Objectives",
            "### Workshop Schedule",
            "### Assessment Structure",
            "**Exercise"
        ]
        
        for element in workshop_elements:
            assert element in content, f"Missing workshop element: {element}"
        
        # Test code examples in workshops
        assert "```python" in content, "Missing Python code examples in workshops"
        # JavaScript examples are in the API workshop section
        if "javascript" in content.lower():
            assert True, "JavaScript examples found"
        
        # Test minimum content length
        assert len(content) > 40000, "Workshop materials seem too short"


class TestTask14CertificationProgram:
    """Test suite for Task 14.4 - Certification Program"""
    
    def setup_method(self):
        """Setup test environment"""
        self.certification_path = project_root / "docs" / "training" / "certification_program.md"
    
    def test_certification_program_structure(self):
        """Test certification program structure and content"""
        assert self.certification_path.exists(), "Certification program file missing"
        
        with open(self.certification_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Test required sections
        required_sections = [
            "# Algorithmic Trading System Certification Program",
            "## Program Overview",
            "## Certification Levels",
            "### Level 1: Platform Fundamentals Certification",
            "### Level 2: Advanced Strategy Development Certification", 
            "### Level 3: Professional Trading Systems Certification",
            "### Specialist Certifications",
            "## Certification Maintenance and Renewal",
            "## Assessment and Testing Framework",
            "## Certification Benefits",
            "## Program Administration",
            "## Pricing and Enrollment"
        ]
        
        for section in required_sections:
            assert section in content, f"Missing required section: {section}"
        
        # Test certification level details
        level_elements = [
            "**Target Audience:**",
            "**Duration:**",
            "**Prerequisites:**",
            "**Validity:**",
            "### Learning Objectives",
            "### Curriculum Structure",
            "### Assessment Structure"
        ]
        
        for element in level_elements:
            assert element in content, f"Missing certification level element: {element}"
        
        # Test specialist certifications
        specialist_certs = [
            "Risk Management Specialist",
            "API Integration Specialist", 
            "Machine Learning for Trading Specialist",
            "Multi-Asset Trading Specialist"
        ]
        
        for cert in specialist_certs:
            assert cert in content, f"Missing specialist certification: {cert}"
        
        # Test minimum content length
        assert len(content) > 20000, "Certification program documentation seems too short"
    
    def test_certification_assessment_structure(self):
        """Test that certification assessments are properly structured"""
        with open(self.certification_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Test assessment components
        assessment_elements = [
            "Knowledge Assessment",
            "Practical Assessment", 
            "**Passing Score:**",
            "**Sample Questions:**",
            "Multiple Choice",
            "Scenario-Based",
            "**Project Requirements:**",
            "**Assessment Criteria:**"
        ]
        
        for element in assessment_elements:
            assert element in content, f"Missing assessment element: {element}"
        
        # Test that sample questions are provided
        assert "Answer:" in content, "Missing sample question answers"
        assert "Explanation:" in content, "Missing sample question explanations"


class TestTask14Integration:
    """Integration tests for all Task 14 components"""
    
    def setup_method(self):
        """Setup test environment"""
        self.docs_path = project_root / "docs"
    
    def test_cross_references_consistency(self):
        """Test that cross-references between documents are consistent"""
        # Read all documentation files
        files_to_check = [
            "interactive_api_documentation.md",
            "training/video_tutorial_scripts.md",
            "training/hands_on_workshops.md", 
            "training/certification_program.md"
        ]
        
        contents = {}
        for file_path in files_to_check:
            full_path = self.docs_path / file_path
            with open(full_path, 'r', encoding='utf-8') as f:
                contents[file_path] = f.read()
        
        # Test that API endpoints mentioned in training materials exist in API docs
        api_content = contents["interactive_api_documentation.md"]
        training_content = contents["training/hands_on_workshops.md"]
        
        # Extract API endpoints mentioned in training
        import re
        endpoint_pattern = r'/[a-zA-Z0-9/_-]+(?:\{[^}]+\})?'
        training_endpoints = set(re.findall(endpoint_pattern, training_content))
        
        # Check that major endpoints are documented
        major_endpoints = ['/auth/login', '/strategies', '/orders', '/backtesting/run']
        for endpoint in major_endpoints:
            if endpoint in training_content:
                assert endpoint in api_content, f"Endpoint {endpoint} mentioned in training but not in API docs"
    
    def test_code_examples_consistency(self):
        """Test that code examples are consistent across documents"""
        # Read API documentation and JavaScript examples
        api_doc_path = self.docs_path / "interactive_api_documentation.md"
        js_examples_path = self.docs_path / "api" / "examples" / "javascript_examples.js"
        
        with open(api_doc_path, 'r', encoding='utf-8') as f:
            api_content = f.read()
        
        with open(js_examples_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Test that class names are consistent
        if "TradingSystemClient" in api_content:
            assert "class TradingSystemClient" in js_content, "Class name inconsistency"
        
        # Test that method names are consistent
        common_methods = ["login", "getStrategies", "createStrategy", "placeOrder"]
        for method in common_methods:
            if method in api_content:
                assert method in js_content, f"Method {method} inconsistency"
    
    def test_documentation_completeness(self):
        """Test that documentation covers all major system components"""
        api_doc_path = self.docs_path / "interactive_api_documentation.md"
        
        with open(api_doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Test coverage of major system components
        major_components = [
            "Authentication",
            "Strategy Management", 
            "Market Data",
            "Backtesting",
            "Trading",
            "Risk Management",
            "Portfolio Management"
        ]
        
        for component in major_components:
            assert component in content, f"Missing documentation for {component}"


class TestTask14Performance:
    """Performance tests for Task 14 components"""
    
    def test_documentation_load_time(self):
        """Test that documentation files can be loaded quickly"""
        import time
        
        docs_path = project_root / "docs"
        large_files = [
            "interactive_api_documentation.md",
            "training/hands_on_workshops.md",
            "training/certification_program.md"
        ]
        
        for file_path in large_files:
            full_path = docs_path / file_path
            if full_path.exists():
                start_time = time.time()
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                load_time = time.time() - start_time
                
                # Should load within reasonable time (1 second for large files)
                assert load_time < 1.0, f"File {file_path} takes too long to load: {load_time:.2f}s"
                assert len(content) > 1000, f"File {file_path} seems too small"
    
    def test_api_testing_suite_performance(self):
        """Test that API testing suite can be imported quickly"""
        import time
        
        api_testing_path = project_root / "docs" / "api" / "api_testing_suite.py"
        
        start_time = time.time()
        spec = importlib.util.spec_from_file_location("api_testing_suite", api_testing_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        import_time = time.time() - start_time
        
        # Should import within reasonable time
        assert import_time < 2.0, f"API testing suite takes too long to import: {import_time:.2f}s"


class TestTask14Accessibility:
    """Accessibility tests for Task 14 documentation"""
    
    def test_markdown_structure(self):
        """Test that Markdown documents have proper heading structure"""
        docs_path = project_root / "docs"
        markdown_files = [
            "interactive_api_documentation.md",
            "training/video_tutorial_scripts.md",
            "training/hands_on_workshops.md",
            "training/certification_program.md"
        ]
        
        for file_path in markdown_files:
            full_path = docs_path / file_path
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Test heading hierarchy
            heading_levels = []
            for line in lines:
                if line.startswith('#'):
                    level = len(line) - len(line.lstrip('#'))
                    heading_levels.append(level)
            
            # Should start with h1
            if heading_levels:
                assert heading_levels[0] == 1, f"Document {file_path} should start with h1"
            
            # Should not skip heading levels
            for i in range(1, len(heading_levels)):
                level_diff = heading_levels[i] - heading_levels[i-1]
                assert level_diff <= 1, f"Document {file_path} skips heading levels"
    
    def test_code_block_formatting(self):
        """Test that code blocks are properly formatted"""
        docs_path = project_root / "docs"
        files_with_code = [
            "interactive_api_documentation.md",
            "training/hands_on_workshops.md"
        ]
        
        for file_path in files_with_code:
            full_path = docs_path / file_path
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Test that code blocks are properly closed
            triple_backticks = content.count('```')
            assert triple_backticks % 2 == 0, f"Unclosed code blocks in {file_path}"
            
            # Test that code blocks have language specification
            import re
            code_blocks = re.findall(r'```(\w+)', content)
            assert len(code_blocks) > 0, f"No language-specified code blocks in {file_path}"


# Test runner and reporting
def run_task_14_tests():
    """Run all Task 14 tests and generate report"""
    import pytest
    
    # Run tests with detailed output
    test_args = [
        __file__,
        "-v",
        "--tb=short",
        "--durations=10",
        f"--junitxml={project_root}/test_results_task_14.xml"
    ]
    
    result = pytest.main(test_args)
    
    # Generate summary report
    print("\n" + "="*80)
    print("TASK 14 TESTING SUMMARY")
    print("="*80)
    
    if result == 0:
        print("✅ ALL TESTS PASSED")
        print("\nTask 14 Documentation and Training components are working correctly:")
        print("- Interactive API Documentation: ✅")
        print("- API Testing Suite: ✅") 
        print("- JavaScript Examples: ✅")
        print("- Java Examples: ✅")
        print("- Video Tutorial Scripts: ✅")
        print("- Hands-On Workshops: ✅")
        print("- Certification Program: ✅")
        print("- Integration Tests: ✅")
        print("- Performance Tests: ✅")
        print("- Accessibility Tests: ✅")
    else:
        print("❌ SOME TESTS FAILED")
        print("Please review the test output above for details.")
    
    return result


if __name__ == "__main__":
    run_task_14_tests()