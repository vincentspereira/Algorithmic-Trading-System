"""
Repository management system for dependency management.
Handles repository tiering, monitoring, and automated updates.
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import requests

logger = logging.getLogger(__name__)

@dataclass
class BranchProtection:
    """Branch protection rules configuration"""
    requires_pull_request: bool
    required_reviewers: int
    dismiss_stale_reviews: bool
    require_up_to_date: bool

@dataclass
class Dependency:
    """Dependency repository configuration"""
    name: str
    repo: str
    fork: str
    description: str
    customizations: List[str]
    branch_protection: BranchProtection

@dataclass
class TierConfig:
    """Configuration for a dependency tier"""
    name: str
    monitoring_frequency: str
    auto_update: bool
    requires_ccb_approval: bool
    dependencies: List[Dependency]

class RepositoryManager:
    """Manages tiered dependencies and their configurations"""
    
    def __init__(
        self,
        config_path: str,
        github_token: str
    ):
        self.config_path = Path(config_path)
        self.github_token = github_token
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """Load repository management configuration"""
        with open(self.config_path) as f:
            return json.load(f)
            
    def _get_headers(self) -> Dict[str, str]:
        """Get GitHub API headers"""
        return {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
    def setup_fork(
        self,
        repo: str,
        fork: str
    ) -> bool:
        """Fork a repository if it doesn't exist"""
        try:
            # Check if fork exists
            owner, repo_name = fork.split('/')
            url = f"https://api.github.com/repos/{fork}"
            response = requests.get(url, headers=self._get_headers())
            
            if response.status_code == 404:
                # Create fork
                owner, repo_name = repo.split('/')
                url = f"https://api.github.com/repos/{repo}/forks"
                response = requests.post(url, headers=self._get_headers())
                
                if response.status_code != 202:
                    logger.error(f"Failed to fork {repo}: {response.text}")
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"Error setting up fork for {repo}: {str(e)}")
            return False
            
    def setup_branch_protection(
        self,
        repo: str,
        protection: BranchProtection
    ) -> bool:
        """Set up branch protection rules"""
        try:
            url = f"https://api.github.com/repos/{repo}/branches/main/protection"
            
            data = {
                "required_status_checks": {
                    "strict": protection.require_up_to_date,
                    "contexts": ["continuous-integration"]
                },
                "enforce_admins": True,
                "required_pull_request_reviews": {
                    "dismissal_restrictions": {},
                    "dismiss_stale_reviews": protection.dismiss_stale_reviews,
                    "require_code_owner_reviews": True,
                    "required_approving_review_count": protection.required_reviewers
                },
                "restrictions": None
            }
            
            response = requests.put(
                url,
                headers=self._get_headers(),
                json=data
            )
            
            if response.status_code not in (200, 201):
                logger.error(
                    f"Failed to set branch protection for {repo}: {response.text}"
                )
                return False
                
            return True
            
        except Exception as e:
            logger.error(
                f"Error setting branch protection for {repo}: {str(e)}"
            )
            return False
            
    def setup_tier(
        self,
        tier: str,
        tier_config: TierConfig
    ) -> bool:
        """Set up all repositories in a tier"""
        success = True
        
        for dep in tier_config.dependencies:
            # Setup fork
            if not self.setup_fork(dep.repo, dep.fork):
                success = False
                continue
                
            # Setup branch protection
            if not self.setup_branch_protection(
                dep.fork,
                dep.branch_protection
            ):
                success = False
                continue
                
            logger.info(f"Successfully set up {dep.name} in {tier}")
            
        return success
        
    def setup_all_tiers(self) -> bool:
        """Set up all tiers and their repositories"""
        success = True
        
        for tier, config in self.config["tiers"].items():
            tier_config = TierConfig(
                name=config["name"],
                monitoring_frequency=config["monitoring_frequency"],
                auto_update=config["auto_update"],
                requires_ccb_approval=config["requires_ccb_approval"],
                dependencies=[
                    Dependency(
                        name=d["name"],
                        repo=d["repo"],
                        fork=d["fork"],
                        description=d["description"],
                        customizations=d["customizations"],
                        branch_protection=BranchProtection(
                            **d["branch_protection"]
                        )
                    )
                    for d in config["dependencies"]
                ]
            )
            
            if not self.setup_tier(tier, tier_config):
                success = False
                
        return success
        
    def get_dependency_status(
        self,
        repo: str
    ) -> Dict:
        """Get dependency status including vulnerabilities"""
        try:
            url = f"https://api.github.com/repos/{repo}/vulnerability-alerts"
            headers = {
                **self._get_headers(),
                "Accept": "application/vnd.github.dorian-preview+json"
            }
            
            response = requests.get(url, headers=headers)
            vulnerabilities = []
            
            if response.status_code == 200:
                vulnerabilities = response.json()
                
            # Get latest commit
            url = f"https://api.github.com/repos/{repo}/commits/main"
            response = requests.get(url, headers=self._get_headers())
            latest_commit = None
            
            if response.status_code == 200:
                latest_commit = response.json()["sha"]
                
            return {
                "vulnerabilities": vulnerabilities,
                "latest_commit": latest_commit,
                "last_checked": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting status for {repo}: {str(e)}")
            return None
            
    def get_tier_status(
        self,
        tier: str
    ) -> Dict:
        """Get status of all dependencies in a tier"""
        status = {}
        tier_config = self.config["tiers"][tier]
        
        for dep in tier_config["dependencies"]:
            status[dep["name"]] = self.get_dependency_status(dep["fork"])
            
        return status
        
def main():
    """Main entry point for repository management"""
    logging.basicConfig(level=logging.INFO)
    
    config_path = os.getenv(
        "REPO_CONFIG",
        "config/repository_management.json"
    )
    github_token = os.getenv("GITHUB_TOKEN")
    
    if not github_token:
        raise ValueError("GITHUB_TOKEN environment variable not set")
        
    manager = RepositoryManager(config_path, github_token)
    
    # Setup all tiers
    if manager.setup_all_tiers():
        logger.info("Successfully set up all repository tiers")
    else:
        logger.error("Failed to set up some repositories")
        
if __name__ == "__main__":
    main()
