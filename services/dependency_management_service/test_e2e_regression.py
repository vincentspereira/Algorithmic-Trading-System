#!/usr/bin/env python3
"""
Test script for end-to-end regression testing framework.
Validates the E2E testing functionality and runs comprehensive tests.
"""

import asyncio
import json
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import sys

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from e2e_regression_tests import E2ERegressionTestFramework

class TestE2ERegressionFramework:
    """Test suite for E2E regression testing framework."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_e2e_config.yaml")
        
        # Change to temp directory
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        self.framework = E2ERegressionTestFramework(self.config_path)
    
    def teardown_method(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_framework_initialization(self):
        """Test framework initialization."""
        assert self.framework is not None
        assert self.framework.config is not None
        assert Path(self.config_path).exists()
        
        # Check default configuration
        assert "test_environment" in self.framework.config
        assert "tier_tests" in self.framework.config
        assert "integration_points" in self.framework.config
        assert "performance_benchmarks" in self.framework.config
    
    def test_config_loading(self):
        """Test configuration loading."""
        config = self.framework.config
        
        # Verify tier configurations
        assert "tier1" in config["tier_tests"]
        assert "tier2" in config["tier_tests"]
        assert "tier3" in config["tier_tests"]
        assert "tier4" in config["tier_tests"]
        
        # Verify critical dependencies for tier1
        tier1_deps = config["tier_tests"]["tier1"]["critical_dependencies"]
        assert "nautilus_trader" in tier1_deps
        assert "kafka" in tier1_deps
        assert "langchain" in tier1_deps
        assert "fastapi" in tier1_deps
    
    @pytest.mark.asyncio
    async def test_dependency_scenarios(self):
        """Test dependency scenario execution."""
        # Mock external calls
        with patch('requests.post') as mock_post, \
             patch('requests.get') as mock_get:
            
            # Mock successful responses
            mock_post.return_value.status_code = 200
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"latest_version": "1.1.0"}
            
            # Test dependency update simulation
            result = await self.framework._test_dependency_update_simulation("nautilus_trader")
            assert result["success"] is True
            assert "Update simulation completed successfully" in result["details"]
    
    @pytest.mark.asyncio
    async def test_security_vulnerability_response(self):
        """Test security vulnerability response workflow."""
        with patch('requests.post') as mock_post, \
             patch('requests.get') as mock_get:
            
            # Mock successful vulnerability alert
            mock_post.return_value.status_code = 200
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = [
                {"cve_id": "CVE-2025-TEST", "severity": "HIGH"}
            ]
            
            result = await self.framework._test_security_vulnerability_response("kafka")
            assert result["success"] is True
            assert "Security vulnerability response completed" in result["details"]
    
    @pytest.mark.asyncio
    async def test_critical_rollback(self):
        """Test critical rollback functionality."""
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 201
            
            result = await self.framework._test_critical_rollback("langchain")
            assert result["success"] is True
            assert "Rollback test completed" in result["details"]
    
    @pytest.mark.asyncio
    async def test_tier_regression_tests(self):
        """Test tier-specific regression testing."""
        # Mock all HTTP requests
        with patch('requests.post') as mock_post, \
             patch('requests.get') as mock_get:
            
            mock_post.return_value.status_code = 200
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"latest_version": "1.1.0"}
            
            # Test tier1 regression
            result = await self.framework.run_tier_regression_tests("tier1")
            
            assert result["tier"] == "tier1"
            assert "dependencies_tested" in result
            assert "success_count" in result
            assert "failure_count" in result
            assert result["within_tolerance"] is True
    
    @pytest.mark.asyncio
    async def test_integration_points(self):
        """Test integration point testing."""
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            
            result = await self.framework.test_integration_points()
            
            assert "kafka_event_flow" in result
            assert "api_contracts" in result
            assert "database_consistency" in result
            assert "performance_benchmarks" in result
    
    @pytest.mark.asyncio
    async def test_api_contracts(self):
        """Test API contract validation."""
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            
            result = await self.framework._test_api_contracts()
            
            assert result["success"] is True
            assert "details" in result
            assert len(result["details"]["tested"]) > 0
    
    @pytest.mark.asyncio
    async def test_performance_benchmarks(self):
        """Test performance benchmark validation."""
        result = await self.framework._test_performance_benchmarks()
        
        assert result["success"] is True
        assert "details" in result
        assert "passed" in result["details"]
    
    @pytest.mark.asyncio
    async def test_mock_scenarios(self):
        """Test all mock scenario implementations."""
        dependencies = ["test_dep"]
        scenarios = [
            "high_availability_test",
            "feature_degradation_test", 
            "performance_impact_test",
            "compatibility_matrix_test",
            "ui_functionality_test",
            "no_code_builder_test",
            "user_experience_test",
            "monitoring_functionality_test",
            "infrastructure_resilience_test",
            "operational_overhead_test"
        ]
        
        for scenario in scenarios:
            for dependency in dependencies:
                result = await self.framework._execute_test_scenario(dependency, scenario)
                assert result["success"] is True, f"Scenario {scenario} failed for {dependency}"
                assert "test passed (mocked)" in result["details"]
    
    @pytest.mark.asyncio
    async def test_test_results_saving(self):
        """Test test results saving functionality."""
        test_results = {
            "success": True,
            "timestamp": "2025-08-28T12:00:00",
            "duration_seconds": 120.5,
            "tier_results": {"tier1": {"success_count": 4, "failure_count": 0}},
            "integration_results": {"kafka_event_flow": {"success": True}}
        }
        
        await self.framework._save_test_results(test_results)
        
        # Check that results directory was created
        results_dir = Path("test-results")
        assert results_dir.exists()
        
        # Check that results file was created
        result_files = list(results_dir.glob("e2e_regression_results_*.json"))
        assert len(result_files) > 0
        
        # Verify content
        with open(result_files[0], 'r') as f:
            saved_results = json.load(f)
        assert saved_results["success"] is True
        assert saved_results["duration_seconds"] == 120.5
    
    def test_unknown_scenario_handling(self):
        """Test handling of unknown test scenarios."""
        async def test_unknown():
            result = await self.framework._execute_test_scenario("test_dep", "unknown_scenario")
            assert result["success"] is False
            assert "Unknown scenario" in result["error"]
        
        asyncio.run(test_unknown())
    
    @pytest.mark.asyncio
    async def test_environment_setup_failure_handling(self):
        """Test handling of environment setup failures."""
        # Mock Docker command failure
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "Docker compose failed"
            
            result = await self.framework.setup_test_environment()
            assert result is False
    
    @pytest.mark.asyncio
    async def test_minimal_compose_creation(self):
        """Test minimal Docker Compose file creation."""
        compose_file = "test-compose.yml"
        await self.framework._create_minimal_compose_file(compose_file)
        
        assert Path(compose_file).exists()
        
        # Verify content
        import yaml
        with open(compose_file, 'r') as f:
            compose_data = yaml.safe_load(f)
        
        assert "services" in compose_data
        assert "dependency-monitor" in compose_data["services"]
        assert "test-database" in compose_data["services"]
        assert "test-redis" in compose_data["services"]

class TestE2EIntegration:
    """Integration tests for E2E framework."""
    
    @pytest.mark.asyncio
    async def test_full_regression_mock_run(self):
        """Test full regression suite with mocked external dependencies."""
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "integration_test_config.yaml")
        
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        
        try:
            framework = E2ERegressionTestFramework(config_path)
            
            # Mock all external calls
            with patch.object(framework, 'setup_test_environment', return_value=True), \
                 patch.object(framework, 'cleanup_test_environment'), \
                 patch('requests.post') as mock_post, \
                 patch('requests.get') as mock_get:
                
                mock_post.return_value.status_code = 200
                mock_get.return_value.status_code = 200
                mock_get.return_value.json.return_value = {"latest_version": "1.1.0"}
                
                # Run full regression suite
                results = await framework.run_full_regression_suite()
                
                # Verify results structure
                assert "success" in results
                assert "tier_results" in results
                assert "integration_results" in results
                assert "summary" in results
                
                # Verify all tiers were tested
                assert "tier1" in results["tier_results"]
                assert "tier2" in results["tier_results"]
                assert "tier3" in results["tier_results"]
                assert "tier4" in results["tier_results"]
                
                # Verify summary information
                summary = results["summary"]
                assert "total_dependencies_tested" in summary
                assert "total_scenarios_executed" in summary
                assert summary["total_dependencies_tested"] > 0
                
        finally:
            os.chdir(original_cwd)
            import shutil
            shutil.rmtree(temp_dir)

# Run basic validation test
def test_basic_framework_functionality():
    """Basic smoke test for framework functionality."""
    temp_dir = tempfile.mkdtemp()
    config_path = os.path.join(temp_dir, "smoke_test_config.yaml")
    
    original_cwd = os.getcwd()
    os.chdir(temp_dir)
    
    try:
        framework = E2ERegressionTestFramework(config_path)
        
        # Test basic initialization
        assert framework is not None
        assert framework.config is not None
        
        # Test configuration structure
        config = framework.config
        assert "test_environment" in config
        assert "tier_tests" in config
        
        # Test tier structure
        for tier in ["tier1", "tier2", "tier3", "tier4"]:
            assert tier in config["tier_tests"]
            tier_config = config["tier_tests"][tier]
            assert "test_scenarios" in tier_config
            assert "max_failure_tolerance" in tier_config
            
        print("✅ E2E Regression Testing Framework smoke test passed")
        
    finally:
        os.chdir(original_cwd)
        import shutil
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    # Run smoke test
    test_basic_framework_functionality()
    
    # Run pytest for comprehensive testing
    pytest.main([__file__, "-v"])