"""
Dependency Management System for Algorithmic Trading Platform

This module provides core functionality for managing dependencies across the platform,
including version tracking, update monitoring, and security scanning.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

import requests
from github import Github
from semantic_version import Version

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DependencyTier(Enum):
    """Dependency criticality tiers"""
    TIER1 = 1  # Critical components (e.g., NautilusTrader)
    TIER2 = 2  # Important components (e.g., PyPortfolioOpt)
    TIER3 = 3  # Supporting components (e.g., Blockly)
    TIER4 = 4  # Infrastructure components (e.g., Kubernetes)

@dataclass
class DependencyUpdate:
    """Represents a dependency update"""
    name: str
    current_version: str
    new_version: str
    changelog_url: str
    breaking_changes: bool
    security_fixes: bool
    tier: DependencyTier

class DependencyManager:
    """Manages dependencies across the algorithmic trading platform"""
    
    def __init__(self, config_path: str):
        """Initialize with configuration file path"""
        self.config_path = config_path
        self.config = self._load_config()
        self.github = Github(os.getenv("GITHUB_TOKEN"))
    
    def _load_config(self) -> Dict:
        """Load dependency configuration"""
        with open(self.config_path, 'r') as f:
            return json.load(f)
    
    def check_for_updates(self, tier: DependencyTier) -> List[DependencyUpdate]:
        """Check for updates in specified tier"""
        updates = []
        tier_deps = self.config["tiers"][f"tier{tier.value}"]["dependencies"]
        
        for dep in tier_deps:
            try:
                # Get latest version from GitHub
                repo = self.github.get_repo(dep["repository"].split("github.com/")[1])
                releases = repo.get_releases()
                if releases.totalCount == 0:
                    continue
                
                latest = releases[0]
                current = Version(dep["version"])
                new = Version(latest.tag_name.lstrip('v'))
                
                if new > current:
                    # Check for breaking changes
                    breaking = self._check_breaking_changes(latest.body)
                    security = self._check_security_fixes(latest.body)
                    
                    updates.append(DependencyUpdate(
                        name=dep["name"],
                        current_version=str(current),
                        new_version=str(new),
                        changelog_url=latest.html_url,
                        breaking_changes=breaking,
                        security_fixes=security,
                        tier=tier
                    ))
            except Exception as e:
                logger.error(f"Error checking updates for {dep['name']}: {e}")
        
        return updates
    
    def _check_breaking_changes(self, changelog: str) -> bool:
        """Check if changelog indicates breaking changes"""
        keywords = ["BREAKING CHANGE", "BREAKING CHANGES", "MAJOR VERSION"]
        return any(kw in changelog.upper() for kw in keywords)
    
    def _check_security_fixes(self, changelog: str) -> bool:
        """Check if changelog indicates security fixes"""
        keywords = ["SECURITY", "CVE-", "VULNERABILITY"]
        return any(kw in changelog.upper() for kw in keywords)
    
    def create_update_pr(self, update: DependencyUpdate) -> None:
        """Create PR for dependency update"""
        try:
            # Create branch
            branch_name = f"update-{update.name.lower()}-{update.new_version}"
            
            # Update version in config
            self._update_dependency_version(update)
            
            # Create PR
            title = f"Update {update.name} to version {update.new_version}"
            body = self._generate_pr_body(update)
            
            # Add test requirements based on tier
            if update.tier in [DependencyTier.TIER1, DependencyTier.TIER2]:
                body += "\n\nRequired Tests:\n- [ ] Unit Tests\n- [ ] Integration Tests\n- [ ] Performance Benchmarks"
            
            # Create GitHub PR
            repo = self.github.get_repo(f"{os.getenv('GITHUB_REPOSITORY')}")
            pr = repo.create_pull(
                title=title,
                body=body,
                head=branch_name,
                base="main"
            )
            
            # Add labels
            pr.add_to_labels(
                f"tier-{update.tier.value}",
                "dependency-update",
                "breaking-change" if update.breaking_changes else "",
                "security" if update.security_fixes else ""
            )
            
        except Exception as e:
            logger.error(f"Error creating PR for {update.name}: {e}")
    
    def _update_dependency_version(self, update: DependencyUpdate) -> None:
        """Update dependency version in config file"""
        with open(self.config_path, 'r+') as f:
            config = json.load(f)
            deps = config["tiers"][f"tier{update.tier.value}"]["dependencies"]
            for dep in deps:
                if dep["name"] == update.name:
                    dep["version"] = update.new_version
                    break
            f.seek(0)
            json.dump(config, f, indent=2)
            f.truncate()
    
    def _generate_pr_body(self, update: DependencyUpdate) -> str:
        """Generate PR description"""
        return f"""
## Dependency Update: {update.name}

- **Current Version:** {update.current_version}
- **New Version:** {update.new_version}
- **Tier:** {update.tier.value}
- **Breaking Changes:** {'Yes' if update.breaking_changes else 'No'}
- **Security Fixes:** {'Yes' if update.security_fixes else 'No'}

### Changelog
See changes at: {update.changelog_url}

### Impact Assessment
{'⚠️ This update contains breaking changes and requires careful review.' if update.breaking_changes else ''}
{'🔒 This update includes security fixes.' if update.security_fixes else ''}

### Automated Checks
- [ ] Version compatibility validated
- [ ] Security scan completed
- [ ] Integration tests passed
"""

def main():
    """Main entry point"""
    manager = DependencyManager("dependency_management/dependencies.json")
    
    # Check updates for each tier
    for tier in DependencyTier:
        logger.info(f"Checking updates for {tier.name}...")
        updates = manager.check_for_updates(tier)
        
        for update in updates:
            logger.info(f"Found update for {update.name}: {update.current_version} -> {update.new_version}")
            manager.create_update_pr(update)

if __name__ == "__main__":
    main()
