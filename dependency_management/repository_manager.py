#!/usr/bin/env python3
"""
Repository Management System for Algorithmic Trading System

This script manages the organization of repositories into 4 tiers as specified in the 
dependency management system. It can either:
1. Clone repositories locally into tiered directories (when no GitHub token is available)
2. Fork repositories on GitHub and organize them (when GitHub token is available)

The script reads the tier configuration files and organizes repositories accordingly.
"""

import json
import os
import subprocess
import sys
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# List of large repositories that need special handling
LARGE_REPOS = [
    "https://github.com/huggingface/transformers",
    "https://github.com/pytorch/pytorch",
    "https://github.com/kubernetes/kubernetes",
    "https://github.com/facebook/react",
    "https://github.com/vercel/next.js"
]

@dataclass
class Dependency:
    """Data class for dependency information"""
    name: str
    repository: str
    fork: str
    type: str = ""
    criticality: str = ""
    version: str = "latest"
    customizations: List[str] = None
    monitoring_schedule: str = ""
    alert_threshold: str = ""

class RepositoryManager:
    """Manages repository organization into tiers"""
    
    def __init__(self, base_path: str = None):
        """
        Initialize the repository manager
        
        Args:
            base_path (str): Base path for repository organization. 
                           Defaults to current working directory.
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.forks_path = self.base_path / "forks"
        self.github_token = os.getenv("GITHUB_TOKEN")
        
        # Create tier directories if they don't exist
        for tier in ["tier1", "tier2", "tier3", "tier4"]:
            tier_path = self.forks_path / tier
            tier_path.mkdir(parents=True, exist_ok=True)
            
        logger.info(f"Repository manager initialized with base path: {self.base_path}")
        
    def load_tier_config(self, tier_file: str) -> Dict[str, Any]:
        """
        Load tier configuration from JSON file
        
        Args:
            tier_file (str): Path to the tier configuration file
            
        Returns:
            Dict: Configuration data
        """
        try:
            with open(tier_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading tier config {tier_file}: {e}")
            return {}
            
    def get_repo_name_from_url(self, url: str) -> str:
        """
        Extract repository name from GitHub URL
        
        Args:
            url (str): GitHub repository URL
            
        Returns:
            str: Repository name
        """
        # Handle URLs like https://github.com/owner/repo or https://github.com/owner/repo.git
        parts = url.rstrip('/').split('/')
        if parts[-1].endswith('.git'):
            return parts[-1][:-4]  # Remove .git extension
        return parts[-1]
        
    def get_owner_repo_from_url(self, url: str) -> tuple:
        """
        Extract owner and repository name from GitHub URL
        
        Args:
            url (str): GitHub repository URL
            
        Returns:
            tuple: (owner, repo_name)
        """
        # Handle URLs like https://github.com/owner/repo or https://github.com/owner/repo.git
        parts = url.rstrip('/').split('/')
        owner = parts[-2]
        repo = parts[-1]
        if repo.endswith('.git'):
            repo = repo[:-4]  # Remove .git extension
        return owner, repo
        
    def clone_large_repository(self, repo_url: str, target_path: str) -> bool:
        """
        Clone a large repository with special handling for Windows path limitations
        
        Args:
            repo_url (str): URL of the repository to clone
            target_path (str): Local path to clone to
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if directory already exists
            if os.path.exists(target_path):
                logger.info(f"Repository already exists at {target_path}")
                return True
                
            logger.info(f"Cloning large repository {repo_url} to {target_path}")
            
            # Create target directory
            os.makedirs(target_path, exist_ok=True)
            
            # Initialize git repository
            subprocess.run(["git", "init"], cwd=target_path, capture_output=True)
            
            # Add remote
            subprocess.run(["git", "remote", "add", "origin", repo_url], cwd=target_path, capture_output=True)
            
            # Enable sparse-checkout for large repositories
            subprocess.run(["git", "config", "core.sparseCheckout", "true"], cwd=target_path, capture_output=True)
            
            # Create sparse-checkout file to limit what we checkout
            sparse_checkout_path = os.path.join(target_path, ".git", "info", "sparse-checkout")
            os.makedirs(os.path.dirname(sparse_checkout_path), exist_ok=True)
            
            # Only checkout essential files and directories
            with open(sparse_checkout_path, "w") as f:
                f.write("README.md\n")
                f.write("LICENSE\n")
                f.write("setup.py\n")
                f.write("pyproject.toml\n")
                f.write("requirements.txt\n")
                f.write("src/\n")
                f.write("lib/\n")
                f.write("*.py\n")
            
            # Fetch and checkout
            subprocess.run(["git", "fetch", "--depth", "1", "origin"], cwd=target_path, capture_output=True)
            subprocess.run(["git", "checkout", "FETCH_HEAD"], cwd=target_path, capture_output=True)
            
            logger.info(f"Successfully cloned large repository {repo_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error cloning large repository {repo_url}: {e}")
            # Clean up on failure
            if os.path.exists(target_path):
                shutil.rmtree(target_path, ignore_errors=True)
            return False
        
    def clone_repository(self, repo_url: str, target_path: str) -> bool:
        """
        Clone a repository to the target path with Windows compatibility
        
        Args:
            repo_url (str): URL of the repository to clone
            target_path (str): Local path to clone to
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Handle large repositories specially
        if repo_url in LARGE_REPOS:
            return self.clone_large_repository(repo_url, target_path)
            
        try:
            # Check if directory already exists
            if os.path.exists(target_path):
                logger.info(f"Repository already exists at {target_path}")
                return True
                
            logger.info(f"Cloning {repo_url} to {target_path}")
            
            # For Windows, we need to handle long paths and filename issues
            # Use sparse-checkout for large repositories that might have path issues
            repo_name = os.path.basename(target_path)
            
            # Create temporary directory for cloning
            temp_dir = f"{target_path}_temp"
            
            # Clone with depth 1 to reduce size and avoid some path issues
            result = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, temp_dir],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0:
                # Move from temp directory to target path
                try:
                    shutil.move(temp_dir, target_path)
                    logger.info(f"Successfully cloned {repo_url}")
                    return True
                except Exception as move_error:
                    logger.error(f"Error moving repository from temp directory: {move_error}")
                    # Clean up temp directory
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
                    return False
            else:
                logger.error(f"Failed to clone {repo_url}: {result.stderr}")
                # Clean up temp directory if it exists
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout cloning {repo_url}")
            return False
        except Exception as e:
            logger.error(f"Error cloning {repo_url}: {e}")
            return False
            
    def fork_repository_github(self, repo_url: str, fork_url: str) -> bool:
        """
        Fork a repository on GitHub (requires GitHub token)
        
        Args:
            repo_url (str): URL of the original repository
            fork_url (str): URL of the desired fork
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.github_token:
            logger.warning("GitHub token not available, falling back to local cloning")
            return False
            
        try:
            import requests
            
            # Extract owner and repo from URLs
            source_owner, source_repo = self.get_owner_repo_from_url(repo_url)
            target_owner, target_repo = self.get_owner_repo_from_url(fork_url)
            
            # Check if fork already exists
            fork_api_url = f"https://api.github.com/repos/{target_owner}/{target_repo}"
            headers = {
                "Authorization": f"Bearer {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            response = requests.get(fork_api_url, headers=headers)
            if response.status_code == 200:
                logger.info(f"Fork already exists: {fork_url}")
                return True
            elif response.status_code != 404:
                logger.error(f"Error checking fork existence: {response.status_code}")
                return False
                
            # Create the fork
            fork_create_url = f"https://api.github.com/repos/{source_owner}/{source_repo}/forks"
            payload = {"organization": target_owner} if target_owner != target_repo else {}
            
            response = requests.post(fork_create_url, headers=headers, json=payload)
            if response.status_code in [201, 202]:
                logger.info(f"Successfully created fork: {fork_url}")
                return True
            else:
                logger.error(f"Failed to create fork: {response.status_code} - {response.text}")
                return False
                
        except ImportError:
            logger.warning("Requests library not available, falling back to local cloning")
            return False
        except Exception as e:
            logger.error(f"Error forking repository {repo_url}: {e}")
            return False
            
    def organize_repository(self, dependency: Dependency, tier: str) -> bool:
        """
        Organize a repository according to the tier structure
        
        Args:
            dependency (Dependency): Dependency information
            tier (str): Tier identifier (tier1, tier2, etc.)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Determine target path based on tier
            repo_name = self.get_repo_name_from_url(dependency.repository)
            target_path = str(self.forks_path / tier / repo_name)
            
            # If GitHub token is available, try to fork on GitHub
            if self.github_token:
                if self.fork_repository_github(dependency.repository, dependency.fork):
                    # Clone the fork locally
                    return self.clone_repository(dependency.fork, target_path)
                else:
                    # Fall back to cloning original repository
                    return self.clone_repository(dependency.repository, target_path)
            else:
                # Clone original repository locally
                return self.clone_repository(dependency.repository, target_path)
                
        except Exception as e:
            logger.error(f"Error organizing repository {dependency.name}: {e}")
            return False
            
    def process_tier(self, tier_file: str, tier_name: str) -> bool:
        """
        Process all dependencies in a tier
        
        Args:
            tier_file (str): Path to tier configuration file
            tier_name (str): Name of the tier
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info(f"Processing {tier_name} from {tier_file}")
        
        config = self.load_tier_config(tier_file)
        if not config:
            logger.error(f"Failed to load configuration for {tier_name}")
            return False
            
        dependencies = config.get("dependencies", [])
        success_count = 0
        total_count = len(dependencies)
        
        for dep_data in dependencies:
            try:
                # Create dependency object
                dependency = Dependency(
                    name=dep_data.get("name", ""),
                    repository=dep_data.get("repository", ""),
                    fork=dep_data.get("fork", ""),
                    type=dep_data.get("type", ""),
                    criticality=dep_data.get("criticality", ""),
                    version=dep_data.get("version", "latest"),
                    customizations=dep_data.get("customizations", []),
                    monitoring_schedule=dep_data.get("monitoring_schedule", ""),
                    alert_threshold=dep_data.get("alert_threshold", "")
                )
                
                # Validate required fields
                if not dependency.name or not dependency.repository:
                    logger.warning(f"Skipping dependency with missing name or repository: {dep_data}")
                    continue
                    
                # Organize the repository
                if self.organize_repository(dependency, tier_name):
                    success_count += 1
                    logger.info(f"Successfully organized {dependency.name}")
                else:
                    logger.error(f"Failed to organize {dependency.name}")
                    
            except Exception as e:
                logger.error(f"Error processing dependency: {e}")
                continue
                
        logger.info(f"Completed {tier_name}: {success_count}/{total_count} repositories organized")
        return success_count == total_count
        
    def process_all_tiers(self) -> bool:
        """
        Process all tier configuration files
        
        Returns:
            bool: True if all tiers processed successfully, False otherwise
        """
        tiers_path = self.base_path / "dependency_management" / "tiers"
        if not tiers_path.exists():
            logger.error(f"Tiers directory not found: {tiers_path}")
            return False
            
        tier_files = {
            "tier1": tiers_path / "tier1_critical.json",
            "tier2": tiers_path / "tier2_important.json", 
            "tier3": tiers_path / "tier3_supporting.json",
            "tier4": tiers_path / "tier4_infrastructure.json"
        }
        
        overall_success = True
        
        for tier_name, tier_file in tier_files.items():
            if tier_file.exists():
                if not self.process_tier(str(tier_file), tier_name):
                    logger.error(f"Failed to process {tier_name}")
                    overall_success = False
            else:
                logger.warning(f"Tier file not found: {tier_file}")
                
        return overall_success
        
    def generate_report(self) -> str:
        """
        Generate a report of the repository organization
        
        Returns:
            str: Report content
        """
        report = []
        report.append("REPOSITORY MANAGEMENT REPORT")
        report.append("=" * 40)
        report.append("")
        
        # Count repositories in each tier
        for tier in ["tier1", "tier2", "tier3", "tier4"]:
            tier_path = self.forks_path / tier
            if tier_path.exists():
                repo_count = len([d for d in tier_path.iterdir() if d.is_dir()])
                report.append(f"{tier.upper()}: {repo_count} repositories")
            else:
                report.append(f"{tier.upper()}: 0 repositories (directory not found)")
                
        report.append("")
        report.append("Repository organization completed.")
        
        return "\n".join(report)

def main():
    """Main function to run the repository manager"""
    logger.info("Starting Repository Management System")
    
    # Initialize repository manager
    manager = RepositoryManager()
    
    # Process all tiers
    if manager.process_all_tiers():
        logger.info("All repositories organized successfully")
        
        # Generate and save report
        report = manager.generate_report()
        report_file = manager.base_path / "dependency_management" / "repository_organization_report.txt"
        
        with open(report_file, 'w') as f:
            f.write(report)
            
        logger.info(f"Report saved to {report_file}")
        print(report)
        return 0
    else:
        logger.error("Failed to organize all repositories")
        return 1

if __name__ == "__main__":
    sys.exit(main())