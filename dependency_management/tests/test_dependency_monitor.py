"""Tests for dependency monitoring system."""

import json
import os
from datetime import datetime, timedelta
from unittest import mock

import pytest
import requests

from ..monitoring.dependency_monitor import (DependencyMonitor, DependencyStatus,
                                          UpdateInfo, VulnerabilityInfo)

@pytest.fixture
def config_file():
    """Create a temporary config file"""
    config = {
        "tiers": {
            "tier1": {
                "name": "Critical Core Components",
                "monitoring_frequency": "daily",
                "auto_update": False,
                "requires_ccb_approval": True,
                "dependencies": [
                    {
                        "name": "TestRepo",
                        "repo": "test/repo",
                        "fork": "test/fork",
                        "description": "Test repository",
                        "customizations": ["test"],
                        "branch_protection": {
                            "requires_pull_request": True,
                            "required_reviewers": 2,
                            "dismiss_stale_reviews": True,
                            "require_up_to_date": True
                        }
                    }
                ]
            }
        },
        "monitoring_config": {
            "update_check": {
                "enabled": True,
                "schedule": {
                    "tier1": "*/15 * * * *"
                }
            }
        }
    }
    
    with open("test_config.json", "w") as f:
        json.dump(config, f)
    return "test_config.json"

@pytest.fixture
def monitor(config_file):
    """Create a dependency monitor instance"""
    return DependencyMonitor(config_file, "test-token", "test-nvd-key")

def test_should_run():
    """Test schedule checking"""
    monitor = DependencyMonitor("test.json", "test-token", "test-nvd-key")
    
    # Should run if never run before
    assert monitor._should_run("*/15 * * * *", None)
    
    # Should not run if last run was recent
    last_run = datetime.utcnow()
    assert not monitor._should_run("*/15 * * * *", last_run)
    
    # Should run if enough time has passed
    last_run = datetime.utcnow() - timedelta(minutes=16)
    assert monitor._should_run("*/15 * * * *", last_run)

@mock.patch('requests.get')
def test_check_vulnerabilities(mock_get, monitor):
    """Test vulnerability checking"""
    # Mock GitHub response
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [
        {
            "id": "test-vuln",
            "severity": "HIGH",
            "description": "Test vulnerability",
            "affected_versions": ["1.0.0"],
            "fixed_versions": ["1.0.1"],
            "cve_ids": ["CVE-2025-1234"],
            "created_at": "2025-08-24T00:00:00Z"
        }
    ]
    
    dependency = {
        "name": "TestRepo",
        "repo": "test/repo",
        "fork": "test/fork"
    }
    
    vulnerabilities = monitor.check_vulnerabilities(dependency)
    assert len(vulnerabilities) == 1
    assert vulnerabilities[0].severity == "HIGH"
    assert vulnerabilities[0].cve_ids == ["CVE-2025-1234"]

@mock.patch('requests.get')
def test_check_updates(mock_get, monitor):
    """Test update checking"""
    # Mock responses
    mock_get.side_effect = [
        # Latest release response
        mock.Mock(
            status_code=200,
            json=lambda: {
                "tag_name": "v2.0.0",
                "html_url": "https://github.com/test/repo/releases/v2.0.0",
                "body": "BREAKING CHANGE: Major update",
                "published_at": "2025-08-24T00:00:00Z"
            }
        ),
        # Current version response
        mock.Mock(
            status_code=200,
            json=lambda: {
                "tag_name": "v1.0.0"
            }
        )
    ]
    
    dependency = {
        "name": "TestRepo",
        "repo": "test/repo",
        "fork": "test/fork"
    }
    
    update_info = monitor.check_updates(dependency)
    assert update_info is not None
    assert update_info.current_version == "v1.0.0"
    assert update_info.latest_version == "v2.0.0"
    assert update_info.breaking_changes

@mock.patch.object(DependencyMonitor, 'check_vulnerabilities')
@mock.patch.object(DependencyMonitor, 'check_updates')
def test_monitor_dependency(mock_updates, mock_vulns, monitor):
    """Test dependency monitoring"""
    # Mock vulnerability check
    mock_vulns.return_value = [
        VulnerabilityInfo(
            id="test-vuln",
            severity="HIGH",
            description="Test vulnerability",
            affected_versions=["1.0.0"],
            fix_versions=["1.0.1"],
            cve_ids=["CVE-2025-1234"],
            discovered_date="2025-08-24T00:00:00Z"
        )
    ]
    
    # Mock update check
    mock_updates.return_value = UpdateInfo(
        current_version="v1.0.0",
        latest_version="v2.0.0",
        changelog_url="https://github.com/test/repo/releases/v2.0.0",
        breaking_changes=True,
        security_fixes=False,
        performance_improvements=True,
        release_date="2025-08-24T00:00:00Z"
    )
    
    dependency = {
        "name": "TestRepo",
        "repo": "test/repo",
        "fork": "test/fork"
    }
    
    with mock.patch.object(
        monitor.repo_manager,
        'get_dependency_status',
        return_value={
            "latest_commit": "test-sha",
            "last_checked": "2025-08-24T00:00:00Z"
        }
    ):
        status = monitor.monitor_dependency("tier1", dependency)
        
        assert status.name == "TestRepo"
        assert status.tier == "tier1"
        assert status.health_status == "critical"
        assert len(status.vulnerabilities) == 1
        assert status.available_update is not None
        assert status.available_update.breaking_changes

def test_get_critical_issues(monitor):
    """Test getting critical issues"""
    # Add some test data to cache
    monitor.status_cache = {
        "tier1/TestRepo1": DependencyStatus(
            name="TestRepo1",
            tier="tier1",
            last_check=datetime.utcnow(),
            last_update=datetime.utcnow(),
            current_commit="test-sha",
            vulnerabilities=[
                VulnerabilityInfo(
                    id="test-vuln",
                    severity="CRITICAL",
                    description="Critical vulnerability",
                    affected_versions=["1.0.0"],
                    fix_versions=["1.0.1"],
                    cve_ids=["CVE-2025-1234"],
                    discovered_date="2025-08-24T00:00:00Z"
                )
            ]
        ),
        "tier1/TestRepo2": DependencyStatus(
            name="TestRepo2",
            tier="tier1",
            last_check=datetime.utcnow(),
            last_update=datetime.utcnow(),
            current_commit="test-sha",
            vulnerabilities=[],
            available_update=UpdateInfo(
                current_version="v1.0.0",
                latest_version="v2.0.0",
                changelog_url="https://github.com/test/repo/releases/v2.0.0",
                breaking_changes=True,
                security_fixes=False,
                performance_improvements=True,
                release_date="2025-08-24T00:00:00Z"
            )
        )
    }
    
    critical = monitor.get_critical_issues()
    assert len(critical) == 2
    
    # Check vulnerability issue
    vuln_issue = next(i for i in critical if i["type"] == "vulnerability")
    assert vuln_issue["dependency"] == "TestRepo1"
    assert vuln_issue["tier"] == "tier1"
    
    # Check breaking change issue
    breaking_issue = next(i for i in critical if i["type"] == "breaking_change")
    assert breaking_issue["dependency"] == "TestRepo2"
    assert breaking_issue["tier"] == "tier1"
