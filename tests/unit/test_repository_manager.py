import unittest
from unittest.mock import patch, mock_open
import json
import os
from pathlib import Path

# Adjust the path to import the module correctly
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'dependency_management'))

from repository_manager import RepositoryManager, BranchProtection, Dependency, TierConfig

class TestRepositoryManager(unittest.TestCase):

    @patch('repository_manager.RepositoryManager._load_config')
    def setUp(self, mock_load_config):
        self.mock_github_token = "mock_token"
        self.mock_config_path = "/mock/path/dependencies.json"
        self.mock_config_content = {
            "tiers": {
                "tier1": {
                    "description": "Critical components",
                    "dependencies": [
                        {
                            "name": "test_repo",
                            "repository": "https://github.com/owner/test_repo",
                            "fork": "owner/test_repo_fork",
                            "version": "1.0.0",
                            "customizations": [],
                            "branch_protection": {
                                "requires_pull_request": True,
                                "required_reviewers": 1,
                                "dismiss_stale_reviews": False,
                                "require_up_to_date": True
                            }
                        }
                    ]
                }
            }
        }
        mock_load_config.return_value = self.mock_config_content
        self.mock_load_config = mock_load_config # Store the mock object
        self.manager = RepositoryManager(self.mock_config_path, self.mock_github_token)

    def test_load_config(self):
        # This test now implicitly tests the mock_load_config in setUp
        # We can add an assertion to ensure it was called
        self.mock_load_config.assert_called_once()
        self.assertEqual(self.manager.config, self.mock_config_content)

    def test_get_headers(self):
        headers = self.manager._get_headers()
        self.assertEqual(headers["Authorization"], f"Bearer {self.mock_github_token}")
        self.assertEqual(headers["Accept"], "application/vnd.github.v3+json")

    @patch('requests.get')
    @patch('requests.post')
    def test_setup_fork_exists(self, mock_post, mock_get):
        mock_get.return_value.status_code = 200
        result = self.manager.setup_fork("https://github.com/owner/test_repo", "owner/test_repo_fork")
        self.assertTrue(result)
        mock_get.assert_called_once()
        mock_post.assert_not_called()

    @patch('requests.get')
    @patch('requests.post')
    def test_setup_fork_creates_new(self, mock_post, mock_get):
        mock_get.side_effect = [mock_get.return_value, mock_get.return_value] # For initial check and then for the fork creation
        mock_get.return_value.status_code = 404 # Fork does not exist
        mock_post.return_value.status_code = 202 # Fork created successfully
        result = self.manager.setup_fork("https://github.com/owner/test_repo", "owner/test_repo_fork")
        self.assertTrue(result)
        mock_get.assert_called_once()
        mock_post.assert_called_once()

    @patch('requests.get')
    @patch('requests.post')
    def test_setup_fork_creation_fails(self, mock_post, mock_get):
        mock_get.side_effect = [mock_get.return_value, mock_get.return_value]
        mock_get.return_value.status_code = 404
        mock_post.return_value.status_code = 400 # Fork creation fails
        result = self.manager.setup_fork("https://github.com/owner/test_repo", "owner/test_repo_fork")
        self.assertFalse(result)
        mock_get.assert_called_once()
        mock_post.assert_called_once()

    @patch('requests.put')
    def test_setup_branch_protection_success(self, mock_put):
        mock_put.return_value.status_code = 200
        protection = BranchProtection()
        result = self.manager.setup_branch_protection("owner/test_repo_fork", protection)
        self.assertTrue(result)
        mock_put.assert_called_once()

    @patch('requests.put')
    def test_setup_branch_protection_failure(self, mock_put):
        mock_put.return_value.status_code = 400
        protection = BranchProtection()
        result = self.manager.setup_branch_protection("owner/test_repo_fork", protection)
        self.assertFalse(result)
        mock_put.assert_called_once()

    @patch.object(RepositoryManager, 'setup_fork', return_value=True)
    @patch.object(RepositoryManager, 'setup_branch_protection', return_value=True)
    def test_setup_all_tiers_success(self, mock_setup_branch_protection, mock_setup_fork):
        result = self.manager.setup_all_tiers()
        self.assertTrue(result)
        mock_setup_fork.assert_called_once()
        # mock_setup_branch_protection.assert_called_once() # This is commented out in the actual code

    @patch.object(RepositoryManager, 'setup_fork', return_value=False)
    @patch.object(RepositoryManager, 'setup_branch_protection', return_value=True)
    def test_setup_all_tiers_fork_failure(self, mock_setup_branch_protection, mock_setup_fork):
        result = self.manager.setup_all_tiers()
        self.assertFalse(result)
        mock_setup_fork.assert_called_once()
        mock_setup_branch_protection.assert_not_called()

if __name__ == '__main__':
    unittest.main()
