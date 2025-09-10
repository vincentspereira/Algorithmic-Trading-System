#!/usr/bin/env python3
"""
Script to fork and organize missing repositories into their respective tier directories.
"""

import os
import subprocess
import json
import shutil
from pathlib import Path

# Configuration
WORKSPACE_ROOT = r"c:\Users\Vincent_Pereira\Projects\Algo_Trading_Projects\Trae\Algorithmic Trading System"
FORKS_DIR = os.path.join(WORKSPACE_ROOT, "forks")
DEPENDENCIES_FILE = os.path.join(WORKSPACE_ROOT, "services", "dependency_management_service", "dependencies.json")

def load_dependencies():
    """Load the dependencies from the JSON file."""
    with open(DEPENDENCIES_FILE, 'r') as f:
        return json.load(f)

def get_existing_repos():
    """Get a set of already organized repository names."""
    existing = set()
    for tier in ['tier1', 'tier2', 'tier3', 'tier4']:
        tier_path = os.path.join(FORKS_DIR, tier)
        if os.path.exists(tier_path):
            for repo_dir in os.listdir(tier_path):
                # Remove common suffixes to get base name
                base_name = repo_dir.replace('_temp', '').replace('-temp', '')
                existing.add(base_name.lower())
    return existing

def clone_repository(repo_url, tier_dir, repo_name):
    """Clone a repository to the specified tier directory."""
    # Normalize repo name for filesystem
    normalized_name = repo_name.lower().replace(' ', '-').replace('.', '-')
    repo_path = os.path.join(tier_dir, normalized_name)
    
    # If directory already exists, skip
    if os.path.exists(repo_path):
        print(f"Repository {repo_name} already exists in {tier_dir}")
        return True
    
    try:
        print(f"Cloning {repo_url} to {repo_path}")
        # Use shallow clone to save space and time
        subprocess.run([
            'git', 'clone', '--depth', '1', repo_url, repo_path
        ], check=True, capture_output=True, text=True)
        print(f"Successfully cloned {repo_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to clone {repo_url}: {e}")
        return False

def organize_missing_repositories():
    """Main function to organize all missing repositories."""
    # Load dependencies
    deps_data = load_dependencies()
    
    # Get existing repositories
    existing_repos = get_existing_repos()
    print(f"Found {len(existing_repos)} existing repositories")
    
    # Process each tier
    tier_mapping = {
        'tier1': 'tier1',
        'tier2': 'tier2', 
        'tier3': 'tier3',
        'tier4': 'tier4'
    }
    
    total_processed = 0
    total_success = 0
    
    for tier_key, tier_name in tier_mapping.items():
        tier_dir = os.path.join(FORKS_DIR, tier_name)
        os.makedirs(tier_dir, exist_ok=True)
        
        tier_deps = deps_data['tiers'][tier_key]['dependencies']
        print(f"\nProcessing {len(tier_deps)} repositories in {tier_name}")
        
        for dep in tier_deps:
            repo_name = dep['name']
            repo_url = dep['repository']
            
            # Normalize repo name for comparison
            normalized_name = repo_name.lower().replace(' ', '-').replace('.', '-')
            
            # Check if already exists
            if normalized_name in existing_repos or repo_name.lower() in existing_repos:
                print(f"Skipping {repo_name} - already exists")
                continue
                
            # Clone the repository
            success = clone_repository(repo_url, tier_dir, repo_name)
            total_processed += 1
            if success:
                total_success += 1
                existing_repos.add(normalized_name)
            
            # Add a small delay to avoid overwhelming GitHub
            import time
            time.sleep(1)
    
    print(f"\nCompleted processing {total_processed} repositories")
    print(f"Successfully cloned {total_success} repositories")
    print(f"Failed to clone {total_processed - total_success} repositories")

if __name__ == "__main__":
    organize_missing_repositories()