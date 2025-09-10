#!/usr/bin/env python3
"""
Script to verify that all repositories from dependencies.json are properly organized.
"""

import os
import json
from pathlib import Path

# Configuration
WORKSPACE_ROOT = r"c:\Users\Vincent_Pereira\Projects\Algo_Trading_Projects\Trae\Algorithmic Trading System"
FORKS_DIR = os.path.join(WORKSPACE_ROOT, "forks")
DEPENDENCIES_FILE = os.path.join(WORKSPACE_ROOT, "services", "dependency_management_service", "dependencies.json")

def load_dependencies():
    """Load the dependencies from the JSON file."""
    with open(DEPENDENCIES_FILE, 'r') as f:
        return json.load(f)

def normalize_repo_name(name):
    """Normalize repository name for comparison."""
    return name.lower().replace(' ', '-').replace('.', '-').replace('_', '-')

def verify_repositories():
    """Verify that all repositories are organized."""
    # Load dependencies
    deps_data = load_dependencies()
    
    # Track verification results
    total_repos = 0
    found_repos = 0
    missing_repos = []
    
    # Process each tier
    tier_mapping = {
        'tier1': 'tier1',
        'tier2': 'tier2', 
        'tier3': 'tier3',
        'tier4': 'tier4'
    }
    
    for tier_key, tier_name in tier_mapping.items():
        tier_dir = os.path.join(FORKS_DIR, tier_name)
        
        # Get list of directories in tier
        if os.path.exists(tier_dir):
            tier_dirs = [d.lower() for d in os.listdir(tier_dir) if os.path.isdir(os.path.join(tier_dir, d))]
        else:
            tier_dirs = []
        
        tier_deps = deps_data['tiers'][tier_key]['dependencies']
        print(f"\nVerifying {len(tier_deps)} repositories in {tier_name}")
        
        for dep in tier_deps:
            total_repos += 1
            repo_name = dep['name']
            normalized_name = normalize_repo_name(repo_name)
            
            # Check if repository exists in tier
            if normalized_name in tier_dirs:
                print(f"  ✅ {repo_name}")
                found_repos += 1
            else:
                # Try with original name
                if repo_name.lower() in tier_dirs:
                    print(f"  ✅ {repo_name}")
                    found_repos += 1
                else:
                    print(f"  ❌ {repo_name} - MISSING")
                    missing_repos.append(f"{tier_name}: {repo_name}")
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"Verification Summary:")
    print(f"Total repositories expected: {total_repos}")
    print(f"Repositories found: {found_repos}")
    print(f"Repositories missing: {len(missing_repos)}")
    
    if missing_repos:
        print("\nMissing repositories:")
        for repo in missing_repos:
            print(f"  - {repo}")
        return False
    else:
        print("\n✅ All repositories have been successfully organized!")
        return True

if __name__ == "__main__":
    verify_repositories()