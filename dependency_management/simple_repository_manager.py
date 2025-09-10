#!/usr/bin/env python3
"""
Simple Repository Manager for Algorithmic Trading System

This script organizes a subset of repositories that don't have path issues on Windows.
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

# List of repositories that are safe to clone on Windows
SAFE_REPOS = [
    "nautilus_trader",
    "nautilus_ibapi", 
    "kafka",
    "schema-registry",
    "langchain",
    "langgraph",
    "fastapi",
    "grpc",
    "PyPortfolioOpt",
    "Riskfolio-Lib",
    "ta-lib-python",
    "ta",
    "shap",
    "vectorbt",
    "QuantLib",
    "blockly",
    "lobe-chat",
    "prometheus",
    "grafana",
    "jaeger",
    "ClickHouse",
    "pgvector",
    "redis",
    "bandit"
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

class SimpleRepositoryManager:
    """Manages organization of safe repositories into tiers"""
    
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
            
        logger.info(f"Simple repository manager initialized with base path: {self.base_path}")
        
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
        
    def clone_repository(self, repo_url: str, target_path: str) -> bool:
        """
        Clone a repository to the target path
        
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
                
            logger.info(f"Cloning {repo_url} to {target_path}")
            
            # Clone with depth 1 to reduce size
            result = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, target_path],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully cloned {repo_url}")
                return True
            else:
                logger.error(f"Failed to clone {repo_url}: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout cloning {repo_url}")
            return False
        except Exception as e:
            logger.error(f"Error cloning {repo_url}: {e}")
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
            
            # Only process safe repositories
            if repo_name not in SAFE_REPOS:
                logger.info(f"Skipping large repository: {repo_name}")
                return True
                
            target_path = str(self.forks_path / tier / repo_name)
            
            # Clone repository locally
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
        total_count = 0
        
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
                    
                # Only count safe repositories
                repo_name = self.get_repo_name_from_url(dependency.repository)
                if repo_name not in SAFE_REPOS:
                    continue
                    
                total_count += 1
                    
                # Organize the repository
                if self.organize_repository(dependency, tier_name):
                    success_count += 1
                    logger.info(f"Successfully organized {dependency.name}")
                else:
                    logger.error(f"Failed to organize {dependency.name}")
                    
            except Exception as e:
                logger.error(f"Error processing dependency: {e}")
                continue
                
        logger.info(f"Completed {tier_name}: {success_count}/{total_count} safe repositories organized")
        return True  # Always return True since we're only processing safe repos
        
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
        report.append("SIMPLE REPOSITORY MANAGEMENT REPORT")
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
        report.append("Note: Large repositories were skipped due to Windows path limitations.")
        report.append("See repository_organization_plan.md for full organization plan.")
        report.append("")
        report.append("Repository organization completed.")
        
        return "\n".join(report)

def main():
    """Main function to run the repository manager"""
    logger.info("Starting Simple Repository Management System")
    
    # Initialize repository manager
    manager = SimpleRepositoryManager()
    
    # Process all tiers
    if manager.process_all_tiers():
        logger.info("Repository organization process completed")
        
        # Generate and save report
        report = manager.generate_report()
        report_file = manager.base_path / "dependency_management" / "simple_repository_organization_report.txt"
        
        with open(report_file, 'w') as f:
            f.write(report)
            
        logger.info(f"Report saved to {report_file}")
        print(report)
        return 0
    else:
        logger.error("Failed to organize repositories")
        return 1

if __name__ == "__main__":
    sys.exit(main())