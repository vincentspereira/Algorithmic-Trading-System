"""
Repository management system for dependency management.
Handles repository tiering, monitoring, and automated updates.
"""

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import requests
from requests.exceptions import RequestException

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@dataclass
class BranchProtection:
    """Branch protection rules configuration"""
    requires_pull_request: bool = True
    required_reviewers: int = 1
    dismiss_stale_reviews: bool = False
    require_up_to_date: bool = True

@dataclass
class Dependency:
    """Dependency repository configuration"""
    name: str
    repository: str
    fork: str
    version: str
    customizations: List[str]
    branch_protection: BranchProtection

@dataclass
class TierConfig:
    """Configuration for a dependency tier"""
    description: str
    dependencies: List[Dependency]

class RepositoryManager:
    """Manages tiered dependencies and their configurations"""

    def __init__(self, config_path: str, github_token: str):
        self.config_path = Path(config_path)
        self.github_token = github_token
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load repository management configuration"""
        logging.info(f"Attempting to load configuration from {self.config_path}")
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error(f"Configuration file not found: {self.config_path}")
            sys.exit(1)
        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON from configuration file: {self.config_path}. Please check its format.")
            sys.exit(1)
        except Exception as e:
            logging.error(f"An unexpected error occurred while loading configuration: {e}")
            sys.exit(1)

    def _get_headers(self) -> Dict[str, str]:
        """Get GitHub API headers"""
        return {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

    def setup_fork(self, repo: str, fork_name: str) -> bool:
        """Fork a repository if it doesn't exist"""
        logging.info(f"Checking fork status for {fork_name} from {repo}")
        owner, _ = fork_name.split('/')
        fork_url = f"https://api.github.com/repos/{fork_name}"
        try:
            response = requests.get(fork_url, headers=self._get_headers())

            if response.status_code == 200:
                logging.info(f"Fork {fork_name} already exists.")
                return True

            if response.status_code == 404:
                logging.info(f"Fork {fork_name} does not exist. Attempting to create fork...")
                source_owner, source_repo = repo.split('/')[-2:]
                fork_api_url = f"https://api.github.com/repos/{source_owner}/{source_repo}/forks"
                fork_payload = {"organization": owner} if owner != self.github_token else {}
                response = requests.post(fork_api_url, headers=self._get_headers(), json=fork_payload)

                if response.status_code in [202, 201]:
                    logging.info(f"Successfully created fork {fork_name}")
                    return True
                else:
                    logging.error(f"Failed to create fork for {repo}. Status: {response.status_code}, Response: {response.text}")
                    return False
            else:
                logging.error(f"Error checking fork {fork_name}. Status: {response.status_code}, Response: {response.text}")
                return False
        except RequestException as e:
            logging.error(f"Network error while setting up fork for {repo}: {e}")
            return False
        except Exception as e:
            logging.error(f"An unexpected error occurred during fork setup for {repo}: {e}")
            return False

    def setup_branch_protection(self, repo_name: str, protection: BranchProtection) -> bool:
        """Set up branch protection rules for the main branch"""
        logging.info(f"Setting up branch protection for {repo_name}")
        protection_url = f"https://api.github.com/repos/{repo_name}/branches/main/protection"
        
        data = {
            "required_status_checks": None,
            "enforce_admins": True,
            "required_pull_request_reviews": {
                "dismiss_stale_reviews": protection.dismiss_stale_reviews,
                "require_code_owner_reviews": False,
                "required_approving_review_count": protection.required_reviewers
            },
            "restrictions": None
        }

        try:
            response = requests.put(protection_url, headers=self._get_headers(), json=data)

            if response.status_code == 200:
                logging.info(f"Successfully set branch protection for {repo_name}")
                return True
            else:
                logging.error(f"Failed to set branch protection for {repo_name}. Status: {response.status_code}, Response: {response.text}")
                return False
        except RequestException as e:
            logging.error(f"Network error while setting up branch protection for {repo_name}: {e}")
            return False
        except Exception as e:
            logging.error(f"An unexpected error occurred during branch protection setup for {repo_name}: {e}")
            return False

    def setup_all_tiers(self) -> bool:
        """Set up all tiers and their repositories"""
        overall_success = True
        for tier_name, tier_data in self.config["tiers"].items():
            logging.info(f"--- Setting up {tier_name} ---")
            for dep_data in tier_data['dependencies']:
                try:
                    # Extract branch_protection and create BranchProtection object
                    bp_data = dep_data.pop('branch_protection', {})
                    protection = BranchProtection(**bp_data)

                    dep = Dependency(branch_protection=protection, **dep_data)

                    logging.info(f"Processing dependency: {dep.name}")
                    
                    if not self.setup_fork(dep.repository, dep.fork):
                        logging.error(f"Skipping {dep.name} due to fork setup failure.")
                        overall_success = False
                        continue
                    
                    # Placeholder for branch protection setup
                    # if not self.setup_branch_protection(dep.fork, dep.branch_protection):
                    #     logging.error(f"Branch protection setup failed for {dep.name}")
                    #     overall_success = False
                except KeyError as e:
                    logging.error(f"Missing key in dependency data for {dep_data.get('name', 'unknown')}: {e}")
                    overall_success = False
                except Exception as e:
                    logging.error(f"An unexpected error occurred while processing dependency {dep_data.get('name', 'unknown')}: {e}")
                    overall_success = False

            logging.info(f"--- Finished {tier_name} ---")
        return overall_success

def main():
    """Main entry point for automated repository management"""
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        logging.error("GITHUB_TOKEN environment variable not set")
        sys.exit(1)

    config_path = Path(__file__).parent / "dependencies.json"
    
    manager = RepositoryManager(config_path=str(config_path), github_token=github_token)
    
    if not manager.setup_all_tiers():
        logging.error("Repository management script failed.")
        sys.exit(1)
    
    logging.info("Repository management script completed successfully.")

if __name__ == "__main__":
    main()