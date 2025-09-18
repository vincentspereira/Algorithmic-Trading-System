"""
Pytest configuration and fixtures for dependency management testing.
Provides test fixtures, mocks, and utilities for testing.
"""

import json
import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Union
from unittest.mock import MagicMock, patch

import pytest
import responses
from github import Github
from prometheus_client import CollectorRegistry
from semantic_version import Version

from dependency_management.error_handling.error_manager import (
    ErrorManager,
    ErrorSeverity,
    ErrorCategory
)

@dataclass
class MockDependency:
    """Mock dependency data for testing"""
    name: str
    version: str
    repository: str
    tier: int
    vulnerabilities: List[Dict[str, Any]] = None
    releases: List[Dict[str, Any]] = None
    performance_metrics: Dict[str, Any] = None

@pytest.fixture
def mock_config() -> Dict[str, Any]:
    """Fixture providing mock configuration"""
    return {
        "tiers": {
            "tier1": {
                "dependencies": [
                    {
                        "name": "test-dep-1",
                        "repository": "github.com/test/test-dep-1",
                        "version": "1.0.0"
                    }
                ]
            },
            "tier2": {
                "dependencies": [
                    {
                        "name": "test-dep-2",
                        "repository": "github.com/test/test-dep-2",
                        "version": "2.0.0"
                    }
                ]
            }
        }
    }

@pytest.fixture
def temp_config_file(mock_config: Dict[str, Any]) -> Generator[str, None, None]:
    """Fixture providing temporary configuration file"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        json.dump(mock_config, f)
        
    yield f.name
    os.unlink(f.name)

@pytest.fixture
def mock_github() -> MagicMock:
    """Fixture providing mock Github client"""
    mock = MagicMock(spec=Github)
    
    def get_repo_side_effect(repo_name: str) -> MagicMock:
        mock_repo = MagicMock()
        mock_releases = MagicMock()
        
        if "test-dep-1" in repo_name:
            releases = [
                create_mock_release("2.0.0", "Release 2.0.0"),
                create_mock_release("1.0.0", "Release 1.0.0")
            ]
        else:
            releases = [
                create_mock_release("3.0.0", "Release 3.0.0"),
                create_mock_release("2.0.0", "Release 2.0.0")
            ]
            
        mock_releases.__iter__.return_value = releases
        mock_releases.totalCount = len(releases)
        mock_repo.get_releases.return_value = mock_releases
        return mock_repo
        
    mock.get_repo.side_effect = get_repo_side_effect
    return mock

@pytest.fixture
def mock_error_manager() -> MagicMock:
    """Fixture providing mock error manager"""
    mock = MagicMock(spec=ErrorManager)
    return mock

@pytest.fixture
def mock_performance_metrics() -> Dict[str, Any]:
    """Fixture providing mock performance metrics"""
    return {
        "cpu_usage": 50.0,
        "memory_usage": 1024.0,
        "disk_io": {
            "read": 100.0,
            "write": 50.0
        },
        "scan_duration": 60.0
    }

@pytest.fixture
def mock_vulnerabilities() -> List[Dict[str, Any]]:
    """Fixture providing mock vulnerability data"""
    return [
        {
            "id": "CVE-2025-1234",
            "severity": "HIGH",
            "description": "Test vulnerability 1",
            "affected_versions": ["1.0.0"],
            "fixed_versions": ["1.0.1"]
        },
        {
            "id": "CVE-2025-5678",
            "severity": "MEDIUM",
            "description": "Test vulnerability 2",
            "affected_versions": ["1.0.0", "1.0.1"],
            "fixed_versions": ["1.1.0"]
        }
    ]

@contextmanager
def mock_responses() -> Generator[responses.RequestsMock, None, None]:
    """Context manager for mocking HTTP responses"""
    with responses.RequestsMock() as rsps:
        # Mock vulnerability database API
        rsps.add(
            responses.GET,
            "https://api.example.com/vulnerabilities",
            json={"vulnerabilities": []}
        )
        
        # Mock package registry API
        rsps.add(
            responses.GET,
            "https://api.example.com/packages",
            json={"packages": []}
        )
        
        yield rsps

def create_mock_dependency(
    name: str,
    version: str,
    tier: int,
    vulnerabilities: Optional[List[Dict[str, Any]]] = None,
    releases: Optional[List[Dict[str, Any]]] = None,
    performance_metrics: Optional[Dict[str, Any]] = None
) -> MockDependency:
    """Create a mock dependency for testing"""
    return MockDependency(
        name=name,
        version=version,
        repository=f"github.com/test/{name}",
        tier=tier,
        vulnerabilities=vulnerabilities or [],
        releases=releases or [],
        performance_metrics=performance_metrics or {}
    )

def create_mock_release(
    tag_name: str,
    body: str,
    created_at: Optional[datetime] = None
) -> MagicMock:
    """Create a mock Github release"""
    mock_release = MagicMock()
    mock_release.tag_name = f"v{tag_name}"
    mock_release.body = body
    mock_release.created_at = created_at or datetime.now(timezone.utc)
    mock_release.html_url = f"https://github.com/test/test-dep/releases/tag/v{tag_name}"
    return mock_release

@pytest.fixture
def mock_metrics_registry() -> Generator[CollectorRegistry, None, None]:
    """Fixture providing isolated Prometheus metrics registry"""
    registry = CollectorRegistry()
    with patch('prometheus_client.REGISTRY', registry):
        yield registry

class MockProcess:
    """Mock psutil Process for testing"""
    
    def __init__(self, metrics: Dict[str, Any]):
        self.metrics = metrics
        
    def cpu_percent(self, interval: float = 1.0) -> float:
        return self.metrics.get('cpu_usage', 0.0)
        
    def memory_info(self) -> MagicMock:
        mock = MagicMock()
        mock.rss = self.metrics.get('memory_usage', 0.0) * 1024 * 1024
        return mock
        
    def io_counters(self) -> MagicMock:
        mock = MagicMock()
        disk_io = self.metrics.get('disk_io', {'read': 0.0, 'write': 0.0})
        mock.read_bytes = disk_io['read'] * 1024 * 1024
        mock.write_bytes = disk_io['write'] * 1024 * 1024
        return mock

@pytest.fixture
def mock_process(mock_performance_metrics: Dict[str, Any]) -> MockProcess:
    """Fixture providing mock Process"""
    return MockProcess(mock_performance_metrics)

@pytest.fixture
def integration_test_dir() -> Generator[Path, None, None]:
    """Fixture providing temporary directory for integration tests"""
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir)
        
        # Create test project structure
        (path / "config").mkdir()
        (path / "logs").mkdir()
        (path / "data").mkdir()
        
        yield path

class IntegrationTestBase:
    """Base class for integration tests"""
    
    @pytest.fixture(autouse=True)
    def setup_integration_test(
        self,
        integration_test_dir: Path,
        mock_github: MagicMock,
        mock_metrics_registry: CollectorRegistry
    ):
        """Setup integration test environment"""
        self.test_dir = integration_test_dir
        self.github = mock_github
        self.metrics_registry = mock_metrics_registry
        
        # Create test configuration
        config = {
            "tiers": {
                f"tier{i}": {"dependencies": []}
                for i in range(1, 5)
            }
        }
        
        config_file = self.test_dir / "config" / "dependencies.json"
        with open(config_file, 'w') as f:
            json.dump(config, f)
            
        self.config_file = str(config_file)
        
    def add_test_dependency(
        self,
        name: str,
        version: str,
        tier: int
    ) -> None:
        """Add a test dependency to configuration"""
        with open(self.config_file, 'r') as f:
            config = json.load(f)
            
        config["tiers"][f"tier{tier}"]["dependencies"].append({
            "name": name,
            "repository": f"github.com/test/{name}",
            "version": version
        })
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f)
            
    def get_metrics(self) -> Dict[str, float]:
        """Get current Prometheus metrics"""
        return {
            metric.name: metric._value.get()
            for metric in self.metrics_registry.collect()
            for metric in metric.samples
        }
        
    def assert_metric_value(self, name: str, expected: float) -> None:
        """Assert that a metric has expected value"""
        metrics = self.get_metrics()
        assert name in metrics, f"Metric {name} not found"
        assert metrics[name] == expected, \
            f"Expected {name} = {expected}, got {metrics[name]}"
            
    def assert_metric_increased(self, name: str) -> None:
        """Assert that a metric has increased"""
        metrics = self.get_metrics()
        assert name in metrics, f"Metric {name} not found"
        assert metrics[name] > 0, f"Expected {name} to increase"

def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers",
        "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers",
        "asyncio: mark test to run in an async context"
    )
