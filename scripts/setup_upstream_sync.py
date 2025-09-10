#!/usr/bin/env python3
"""
Script to set up automated synchronization with upstream repositories for all forks.
"""

import os
import subprocess
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

def setup_upstream_sync():
    """Set up upstream synchronization for all forked repositories."""
    # Load dependencies
    deps_data = load_dependencies()
    
    # Process each tier
    tier_mapping = {
        'tier1': 'tier1',
        'tier2': 'tier2', 
        'tier3': 'tier3',
        'tier4': 'tier4'
    }
    
    sync_count = 0
    
    for tier_key, tier_name in tier_mapping.items():
        tier_dir = os.path.join(FORKS_DIR, tier_name)
        
        if not os.path.exists(tier_dir):
            print(f"Tier directory {tier_dir} does not exist, skipping...")
            continue
            
        tier_deps = deps_data['tiers'][tier_key]['dependencies']
        print(f"\nSetting up upstream sync for {len(tier_deps)} repositories in {tier_name}")
        
        for dep in tier_deps:
            repo_name = dep['name']
            upstream_url = dep['repository']
            
            # Normalize repo name for filesystem
            normalized_name = repo_name.lower().replace(' ', '-').replace('.', '-')
            repo_path = os.path.join(tier_dir, normalized_name)
            
            # Check if repository exists
            if not os.path.exists(repo_path):
                # Try with original name
                repo_path = os.path.join(tier_dir, repo_name)
                if not os.path.exists(repo_path):
                    print(f"  ❌ Repository {repo_name} not found, skipping...")
                    continue
            
            try:
                # Change to repository directory
                os.chdir(repo_path)
                
                # Add upstream remote if it doesn't exist
                result = subprocess.run(['git', 'remote', 'get-url', 'upstream'], 
                                      capture_output=True, text=True)
                
                if result.returncode != 0:
                    # Upstream doesn't exist, add it
                    subprocess.run(['git', 'remote', 'add', 'upstream', upstream_url], 
                                 check=True, capture_output=True)
                    print(f"  ✅ Added upstream for {repo_name}")
                else:
                    # Upstream exists, update it
                    subprocess.run(['git', 'remote', 'set-url', 'upstream', upstream_url], 
                                 check=True, capture_output=True)
                    print(f"  ✅ Updated upstream for {repo_name}")
                
                sync_count += 1
                
            except subprocess.CalledProcessError as e:
                print(f"  ❌ Error setting up upstream for {repo_name}: {e}")
            except Exception as e:
                print(f"  ❌ Error processing {repo_name}: {e}")
    
    print(f"\nCompleted setting up upstream sync for {sync_count} repositories")

def create_sync_script():
    """Create a batch script for periodic synchronization."""
    script_content = """@echo off
REM Automated synchronization script for all forked repositories

echo Starting automated synchronization of all forked repositories...

cd /d "c:\\Users\\Vincent_Pereira\\Projects\\Algo_Trading_Projects\\Trae\\Algorithmic Trading System"

python scripts\\sync_forks_with_upstream.py

echo Synchronization complete.

pause
"""
    
    script_path = os.path.join(WORKSPACE_ROOT, "scripts", "sync_all_forks.bat")
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    print(f"Created synchronization script at {script_path}")

if __name__ == "__main__":
    setup_upstream_sync()
    create_sync_script()
    print("\n✅ Upstream synchronization setup complete!")
    print("Use 'scripts\\sync_all_forks.bat' to manually sync all repositories")