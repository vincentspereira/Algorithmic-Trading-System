"""
Integration tests for the Dependency Management System.
Tests end-to-end functionality across all services.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
import pytest
from unittest.mock import patch
from github.GithubException import RateLimitExceededException

from dependency_management.scripts.dependency_manager import DependencyManager
from dependency_management.error_handling.error_types import (
    DependencyVersionError,
    DependencySecurityError
)
from tests.conftest import IntegrationTestBase, create_mock_release

@pytest.mark.integration
class TestDependencyManagementIntegration(IntegrationTestBase):
    """Integration tests for dependency management"""
    
    def test_check_for_updates_with_new_versions(self):
        """Test checking for updates when new versions are available"""
        # Add test dependencies
        self.add_test_dependency("test-dep-1", "1.0.0", 1)
        self.add_test_dependency("test-dep-2", "2.0.0", 2)
        
        # Create manager and check for updates
        manager = DependencyManager(self.config_file)
        updates = manager.check_for_updates()
        
        # Verify updates were found
        assert len(updates) == 2
        
        # Verify first update
        assert updates[0].name == "test-dep-1"
        assert updates[0].current_version == "1.0.0"
        assert updates[0].new_version == "2.0.0"
        
        # Verify second update
        assert updates[1].name == "test-dep-2"
        assert updates[1].current_version == "2.0.0"
        assert updates[1].new_version == "3.0.0"
        
    @patch('requests.get')
    def test_security_scanning(self, mock_get):
        """Test security vulnerability scanning"""
        # Mock vulnerability data
        mock_get.return_value.json.return_value = {
            "vulnerabilities": [
                {
                    "id": "CVE-2025-1234",
                    "package": "test-dep-1",
                    "severity": "HIGH",
                    "affected_versions": ["1.0.0"],
                    "description": "Test vulnerability"
                }
            ]
        }
        mock_get.return_value.status_code = 200
        
        # Add vulnerable dependency
        self.add_test_dependency("test-dep-1", "1.0.0", 1)
        
        # Create manager and scan for vulnerabilities
        manager = DependencyManager(self.config_file)
        with pytest.raises(DependencySecurityError) as exc_info:
            manager.scan_dependencies()
            
        # Verify vulnerability was detected
        assert "CVE-2025-1234" in str(exc_info.value)
        assert "test-dep-1" in str(exc_info.value)
        self.assert_metric_increased("dependency_vulnerabilities_total")
        
    def test_performance_monitoring(self):
        """Test performance monitoring and optimization"""
        # Add test dependency
        self.add_test_dependency("test-dep-1", "1.0.0", 1)
        
        # Create manager and collect metrics
        manager = DependencyManager(self.config_file)
        
        # Simulate high resource usage
        with patch('psutil.Process') as mock_process:
            mock_process.return_value.cpu_percent.return_value = 90.0
            mock_process.return_value.memory_info.return_value.rss = 2 * 1024 * 1024 * 1024
            
            metrics = manager.collect_performance_metrics("test-dep-1")
            recommendations = manager.get_performance_recommendations("test-dep-1")
            
        # Verify metrics were collected
        assert metrics["cpu_usage"] == 90.0
        assert metrics["memory_usage"] > 1024  # >1GB
        
        # Verify recommendations were generated
        assert len(recommendations) > 0
        assert any(r["priority"] == "high" for r in recommendations)
        
    def test_dependency_updates_with_breaking_changes(self):
        """Test handling of updates with breaking changes"""
        # Add test dependency
        self.add_test_dependency("test-dep-1", "1.0.0", 1)
        
        # Mock breaking changes in release notes
        with patch('github.Github.get_repo') as mock_get_repo:
            mock_repo = mock_get_repo.return_value
            mock_releases = mock_repo.get_releases.return_value
            mock_releases.__iter__.return_value = [
                create_mock_release(
                    "2.0.0",
                    "BREAKING CHANGE: Major API changes"
                )
            ]
            mock_releases.totalCount = 1
            
            # Create manager and check for updates
            manager = DependencyManager(self.config_file)
            updates = manager.check_for_updates()
            
        # Verify breaking change was detected
        assert len(updates) == 1
        assert updates[0].breaking_changes
        self.assert_metric_increased("dependency_breaking_changes_total")
        
    def test_dependency_resolution_conflicts(self):
        """Test handling of dependency resolution conflicts"""
        # Add conflicting dependencies
        self.add_test_dependency("test-dep-1", "1.0.0", 1)
        self.add_test_dependency("test-dep-2", "2.0.0", 1)
        
        # Mock dependency resolution conflict
        with patch('semantic_version.Version.coerce') as mock_coerce:
            mock_coerce.side_effect = ValueError("Invalid version")
            
            # Create manager and attempt resolution
            manager = DependencyManager(self.config_file)
            with pytest.raises(DependencyVersionError) as exc_info:
                manager.resolve_dependencies()
                
        # Verify error was properly handled
        assert "version conflict" in str(exc_info.value).lower()
        self.assert_metric_increased("dependency_resolution_errors_total")
        
    @pytest.mark.performance
    def test_performance_under_load(self):
        """Test system performance under load"""
        # Add multiple dependencies
        for i in range(100):
            self.add_test_dependency(f"test-dep-{i}", "1.0.0", i % 4 + 1)
            
        # Create manager
        manager = DependencyManager(self.config_file)
        
        # Measure operation time
        start_time = datetime.utcnow()
        
        # Perform bulk operations
        updates = manager.check_for_updates()
        manager.collect_performance_metrics("test-dep-0")
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        # Verify performance meets requirements
        assert duration < 5.0  # Should complete within 5 seconds
        assert len(updates) > 0
        
    def test_error_handling_and_recovery(self):
        """Test error handling and recovery mechanisms"""
        # Add test dependency
        self.add_test_dependency("test-dep-1", "1.0.0", 1)
        
        # Create manager
        manager = DependencyManager(self.config_file)
        
        # Test network error handling
        with patch('github.Github.get_repo', side_effect=ConnectionError):
            # Should fall back to cached data
            updates = manager.check_for_updates()
            assert len(updates) == 0
            self.assert_metric_increased("dependency_network_errors_total")
            
        # Test API rate limit handling
        with patch('github.Github.get_repo', side_effect=RateLimitExceededException):
            start_time = datetime.utcnow()
            updates = manager.check_for_updates()
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Should implement backoff
            assert duration >= 1.0
            self.assert_metric_increased("dependency_rate_limit_errors_total")
            
    def test_metric_collection_and_alerting(self):
        """Test metric collection and alerting system"""
        # Add test dependency
        self.add_test_dependency("test-dep-1", "1.0.0", 1)
        
        # Create manager
        manager = DependencyManager(self.config_file)
        
        # Simulate various events
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            
            # Trigger security alert
            manager.handle_security_event({
                "severity": "HIGH",
                "package": "test-dep-1",
                "description": "Test security event"
            })
            
            # Verify alert was sent
            assert mock_post.called
            self.assert_metric_increased("dependency_security_alerts_total")
            
        # Verify metrics were recorded
        metrics = self.get_metrics()
        assert "dependency_checks_total" in metrics
        assert "dependency_scan_duration_seconds" in metrics
import pytest
import pytest_asyncio
from httpx import AsyncClient
import aiohttp
import json
from datetime import datetime, timedelta

# Configure pytest-asyncio to use strict mode
pytestmark = pytest.mark.asyncio

# Test configuration
API_URL = "http://api:8000"
NOTIFICATION_URL = "http://notification:8001"
SECURITY_URL = "http://security:8002"
DASHBOARD_URL = "http://dashboard:3000"

@pytest_asyncio.fixture
async def api_client():
    """Fixture for API client"""
    async with AsyncClient(base_url=API_URL) as client:
        yield client

@pytest.fixture
def test_dependency():
    """Fixture for test dependency data"""
    return {
        "name": "test-dependency",
        "version": "1.0.0",
        "tier": 1,
        "repository": "https://github.com/test/repo"
    }

class TestEndToEnd:
    """End-to-end test scenarios"""

    async def test_dependency_lifecycle(self, api_client, test_dependency):
        """Test complete dependency lifecycle"""
        # 1. Add new dependency
        response = await api_client.post(
            "/api/dependencies",
            json=test_dependency
        )
        assert response.status_code == 200
        dep_id = response.json()["id"]

        # 2. Check health status
        response = await api_client.get(f"/api/dependencies/{dep_id}/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

        # 3. Trigger security scan
        async with AsyncClient(base_url=SECURITY_URL) as security_client:
            response = await security_client.post(
                "/scan",
                json={"dependencies": [test_dependency]}
            )
            assert response.status_code == 200
            scan_id = response.json()["scan_id"]

        # 4. Check security results
        async with AsyncClient(base_url=SECURITY_URL) as security_client:
            response = await security_client.get(f"/vulnerabilities/{scan_id}")
            assert response.status_code == 200
            assert "risk_score" in response.json()

        # 5. Test notification
        async with AsyncClient(base_url=NOTIFICATION_URL) as notification_client:
            response = await notification_client.post(
                "/notify",
                json={
                    "title": "Test Notification",
                    "message": "Testing notification system",
                    "priority": "high",
                    "tier": 1
                }
            )
            assert response.status_code == 200

    async def test_update_workflow(self, api_client, test_dependency):
        """Test dependency update workflow"""
        # 1. Create update PR
        response = await api_client.post(
            f"/api/dependencies/{test_dependency['name']}/update",
            json={"version": "1.1.0"}
        )
        assert response.status_code == 200
        pr_id = response.json()["pr_id"]

        # 2. Run automated tests
        response = await api_client.get(f"/api/dependencies/pr/{pr_id}/tests")
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # 3. Approve update
        response = await api_client.post(
            f"/api/dependencies/pr/{pr_id}/approve"
        )
        assert response.status_code == 200

        # 4. Verify update
        response = await api_client.get(
            f"/api/dependencies/{test_dependency['name']}"
        )
        assert response.status_code == 200
        assert response.json()["version"] == "1.1.0"

    async def test_monitoring_system(self, api_client):
        """Test monitoring and alerting system"""
        # 1. Check all services health
        services = ["api", "notification", "security"]
        for service in services:
            response = await api_client.get(f"/health/{service}")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"

        # 2. Test alert generation
        response = await api_client.post(
            "/api/alerts/test",
            json={
                "type": "security",
                "severity": "high"
            }
        )
        assert response.status_code == 200

        # 3. Verify alert reception
        async with AsyncClient(base_url=NOTIFICATION_URL) as notification_client:
            response = await notification_client.get("/notifications/recent")
            assert response.status_code == 200
            notifications = response.json()["notifications"]
            assert len(notifications) > 0

    async def test_dashboard_integration(self, api_client):
        """Test dashboard data integration"""
        # 1. Get dashboard data
        response = await api_client.get("/api/dashboard/summary")
        assert response.status_code == 200
        data = response.json()

        # 2. Verify data structure
        required_fields = [
            "total_dependencies",
            "healthy_count",
            "warning_count",
            "critical_count",
            "recent_updates",
            "security_alerts"
        ]
        for field in required_fields:
            assert field in data

        # 3. Test real-time updates
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(f"{API_URL}/ws/updates") as ws:
                # Send test update
                await api_client.post(
                    "/api/test/event",
                    json={"type": "dependency_update"}
                )
                
                # Verify WebSocket message
                msg = await ws.receive_json()
                assert msg["type"] == "dependency_update"

class TestSecurityIntegration:
    """Security integration tests"""

    async def test_vulnerability_detection(self, api_client, test_dependency):
        """Test vulnerability detection and reporting"""
        # 1. Submit test vulnerability
        async with AsyncClient(base_url=SECURITY_URL) as security_client:
            response = await security_client.post(
                "/test/vulnerability",
                json={
                    "dependency": test_dependency["name"],
                    "cve_id": "TEST-CVE-2025-0001",
                    "severity": "high"
                }
            )
            assert response.status_code == 200

        # 2. Check vulnerability detection
        response = await api_client.get(
            f"/api/security/vulnerabilities/{test_dependency['name']}"
        )
        assert response.status_code == 200
        vulns = response.json()["vulnerabilities"]
        assert len(vulns) > 0
        assert vulns[0]["cve_id"] == "TEST-CVE-2025-0001"

        # 3. Verify notification
        async with AsyncClient(base_url=NOTIFICATION_URL) as notification_client:
            response = await notification_client.get("/notifications/security")
            assert response.status_code == 200
            assert len(response.json()["notifications"]) > 0

class TestPerformance:
    """Performance and load tests"""

    async def test_update_check_performance(self, api_client):
        """Test update check performance"""
        start_time = datetime.now()
        
        # Run update check for all dependencies
        response = await api_client.post("/api/dependencies/check-updates")
        assert response.status_code == 200
        
        duration = datetime.now() - start_time
        assert duration < timedelta(seconds=5)  # Should complete within 5 seconds

    async def test_concurrent_requests(self, api_client):
        """Test system under concurrent load"""
        async def make_request():
            return await api_client.get("/api/dependencies/health")

        # Make 50 concurrent requests
        tasks = [make_request() for _ in range(50)]
        responses = await asyncio.gather(*tasks)
        
        # Verify all requests succeeded
        assert all(r.status_code == 200 for r in responses)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
