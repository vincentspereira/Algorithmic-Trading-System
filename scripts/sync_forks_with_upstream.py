#!/usr/bin/env python3
"""
Script to synchronize all forked repositories with their upstream repositories.
"""

import os
import subprocess
import json
import time
from pathlib import Path

# Configuration
WORKSPACE_ROOT = r"c:\Users\Vincent_Pereira\Projects\Algo_Trading_Projects\Trae\Algorithmic Trading System"
FORKS_DIR = os.path.join(WORKSPACE_ROOT, "forks")
DEPENDENCIES_FILE = os.path.join(WORKSPACE_ROOT, "services", "dependency_management_service", "dependencies.json")

def load_dependencies():
    """Load the dependencies from the JSON file."""
    with open(DEPENDENCIES_FILE, 'r') as f:
        return json.load(f)

def sync_repository(repo_path, repo_name):
    """Synchronize a single repository with its upstream."""
    try:
        # Change to repository directory
        original_dir = os.getcwd()
        os.chdir(repo_path)
        
        # Fetch upstream changes
        print(f"  Fetching upstream changes for {repo_name}...")
        subprocess.run(['git', 'fetch', 'upstream'], check=True, capture_output=True)
        
        # Get current branch
        result = subprocess.run(['git', 'branch', '--show-current'], 
                              capture_output=True, text=True)
        current_branch = result.stdout.strip()
        
        if not current_branch:
            # If HEAD is detached, try to get the default branch
            result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
                                  capture_output=True, text=True)
            current_branch = result.stdout.strip()
            
        if current_branch == "HEAD":
            # Try to get default branch from remote
            result = subprocess.run(['git', 'remote', 'show', 'upstream'], 
                                  capture_output=True, text=True)
            lines = result.stdout.split('\n')
            for line in lines:
                if 'HEAD branch' in line:
                    current_branch = line.split(':')[-1].strip()
                    break
        
        if not current_branch or current_branch == "HEAD":
            current_branch = "main"  # Default fallback
            
        print(f"  Current branch for {repo_name}: {current_branch}")
        
        # Merge upstream changes
        print(f"  Merging upstream/{current_branch} into {repo_name}...")
        subprocess.run(['git', 'merge', f'upstream/{current_branch}'], 
                      check=True, capture_output=True)
        
        # Push changes to origin
        print(f"  Pushing changes for {repo_name}...")
        subprocess.run(['git', 'push', 'origin', current_branch], 
                      check=True, capture_output=True)
        
        os.chdir(original_dir)
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Error synchronizing {repo_name}: {e}")
        # Try to recover
        try:
            subprocess.run(['git', 'reset', '--hard', 'HEAD'], 
                          check=True, capture_output=True)
        except:
            pass
        os.chdir(original_dir)
        return False
    except Exception as e:
        print(f"  ❌ Unexpected error with {repo_name}: {e}")
        os.chdir(original_dir)
        return False

def sync_all_repositories():
    """Synchronize all forked repositories with their upstream repositories."""
    # Load dependencies
    deps_data = load_dependencies()
    
    # Process each tier
    tier_mapping = {
        'tier1': 'tier1',
        'tier2': 'tier2', 
        'tier3': 'tier3',
        'tier4': 'tier4'
    }
    
    total_repos = 0
    successful_syncs = 0
    failed_syncs = 0
    
    for tier_key, tier_name in tier_mapping.items():
        tier_dir = os.path.join(FORKS_DIR, tier_name)
        
        if not os.path.exists(tier_dir):
            print(f"Tier directory {tier_dir} does not exist, skipping...")
            continue
            
        tier_deps = deps_data['tiers'][tier_key]['dependencies']
        print(f"\nSynchronizing {len(tier_deps)} repositories in {tier_name}")
        
        for dep in tier_deps:
            repo_name = dep['name']
            
            # Normalize repo name for filesystem
            normalized_name = repo_name.lower().replace(' ', '-').replace('.', '-')
            repo_path = os.path.join(tier_dir, normalized_name)
            
            # Check if repository exists
            if not os.path.exists(repo_path):
                # Try with original name
                repo_path = os.path.join(tier_dir, repo_name)
                if not os.path.exists(repo_path):
                    print(f"  ❌ Repository {repo_name} not found, skipping...")
                    failed_syncs += 1
                    continue
            
            total_repos += 1
            print(f"  Synchronizing {repo_name}...")
            
            if sync_repository(repo_path, repo_name):
                print(f"  ✅ Successfully synchronized {repo_name}")
                successful_syncs += 1
            else:
                print(f"  ❌ Failed to synchronize {repo_name}")
                failed_syncs += 1
            
            # Add a small delay to avoid overwhelming GitHub
            time.sleep(2)
    
    print(f"\n{'='*50}")
    print(f"Synchronization Summary:")
    print(f"Total repositories: {total_repos}")
    print(f"Successful synchronizations: {successful_syncs}")
    print(f"Failed synchronizations: {failed_syncs}")
    
    if failed_syncs == 0:
        print("\n✅ All repositories synchronized successfully!")
    else:
        print(f"\n⚠️  {failed_syncs} repositories failed to synchronize")

if __name__ == "__main__":
    sync_all_repositories()