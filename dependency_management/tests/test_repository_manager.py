"""Tests for repository management system."""

import json
import os
import tempfile
from unittest import mock

import pytest
import requests

from ..repository_manager import (BranchProtection, Dependency,
                                RepositoryManager, TierConfig)

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
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        json.dump(config, f)
        return f.name

@pytest.fixture
def repo_manager(config_file):
    """Create a repository manager instance"""
    return RepositoryManager(config_file, "test-token")

def test_load_config(repo_manager):
    """Test loading configuration"""
    config = repo_manager.config
    assert "tiers" in config
    assert "tier1" in config["tiers"]
    assert len(config["tiers"]["tier1"]["dependencies"]) == 1

@mock.patch('requests.get')
@mock.patch('requests.post')
def test_setup_fork(mock_post, mock_get, repo_manager):
    """Test fork setup"""
    # Mock fork doesn't exist
    mock_get.return_value.status_code = 404
    mock_post.return_value.status_code = 202
    
    assert repo_manager.setup_fork("test/repo", "test/fork")
    mock_post.assert_called_once()
    
    # Mock fork exists
    mock_get.return_value.status_code = 200
    assert repo_manager.setup_fork("test/repo", "test/fork")
    # No new post call
    mock_post.assert_called_once()

@mock.patch('requests.put')
def test_setup_branch_protection(mock_put, repo_manager):
    """Test branch protection setup"""
    mock_put.return_value.status_code = 200
    
    protection = BranchProtection(
        requires_pull_request=True,
        required_reviewers=2,
        dismiss_stale_reviews=True,
        require_up_to_date=True
    )
    
    assert repo_manager.setup_branch_protection("test/fork", protection)
    mock_put.assert_called_once()

@mock.patch.object(RepositoryManager, 'setup_fork')
@mock.patch.object(RepositoryManager, 'setup_branch_protection')
def test_setup_tier(mock_protection, mock_fork, repo_manager):
    """Test tier setup"""
    mock_fork.return_value = True
    mock_protection.return_value = True
    
    tier_config = TierConfig(
        name="Test Tier",
        monitoring_frequency="daily",
        auto_update=False,
        requires_ccb_approval=True,
        dependencies=[
            Dependency(
                name="TestRepo",
                repo="test/repo",
                fork="test/fork",
                description="Test repository",
                customizations=["test"],
                branch_protection=BranchProtection(
                    requires_pull_request=True,
                    required_reviewers=2,
                    dismiss_stale_reviews=True,
                    require_up_to_date=True
                )
            )
        ]
    )
    
    assert repo_manager.setup_tier("tier1", tier_config)
    mock_fork.assert_called_once()
    mock_protection.assert_called_once()

@mock.patch('requests.get')
def test_get_dependency_status(mock_get, repo_manager):
    """Test getting dependency status"""
    # Mock vulnerability response
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "sha": "test-sha"
    }
    
    status = repo_manager.get_dependency_status("test/fork")
    assert status is not None
    assert "vulnerabilities" in status
    assert "latest_commit" in status
    assert "last_checked" in status

def test_get_tier_status(repo_manager):
    """Test getting tier status"""
    with mock.patch.object(
        RepositoryManager,
        'get_dependency_status'
    ) as mock_status:
        mock_status.return_value = {
            "vulnerabilities": [],
            "latest_commit": "test-sha",
            "last_checked": "2025-08-24T00:00:00Z"
        }
        
        status = repo_manager.get_tier_status("tier1")
        assert "TestRepo" in status
        assert status["TestRepo"]["latest_commit"] == "test-sha"

@mock.patch.object(RepositoryManager, 'setup_tier')
def test_setup_all_tiers(mock_setup, repo_manager):
    """Test setting up all tiers"""
    mock_setup.return_value = True
    assert repo_manager.setup_all_tiers()
    mock_setup.assert_called_once()
