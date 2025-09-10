#!/usr/bin/env python3
"""
Script to track customizations made to forked repositories.
"""

import os
import json
import subprocess
from datetime import datetime
from pathlib import Path

# Configuration
WORKSPACE_ROOT = r"c:\\Users\\Vincent_Pereira\\Projects\\Algo_Trading_Projects\\Trae\\Algorithmic Trading System"
FORKS_DIR = os.path.join(WORKSPACE_ROOT, "forks")
CUSTOMIZATION_TRACKING_FILE = os.path.join(WORKSPACE_ROOT, "dependency_management", "customization_tracking.json")

def get_git_diff_stats(repo_path):
    """Get statistics about changes in a repository."""
    try:
        # Change to repository directory
        original_dir = os.getcwd()
        os.chdir(repo_path)
        
        # Get commit count difference
        result = subprocess.run([
            'git', 'rev-list', '--count', 'HEAD'
        ], capture_output=True, text=True)
        
        commit_count = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
        
        # Get changed files
        result = subprocess.run([
            'git', 'diff', '--stat', 'upstream/main..HEAD'
        ], capture_output=True, text=True)
        
        # Count lines of changes
        lines_changed = 0
        if result.stdout:
            for line in result.stdout.split('\n'):
                if 'insertions' in line or 'deletions' in line:
                    # Extract number of changes
                    parts = line.split(',')
                    for part in parts:
                        if 'insertion' in part or 'deletion' in part:
                            num = ''.join(filter(str.isdigit, part))
                            if num:
                                lines_changed += int(num)
        
        os.chdir(original_dir)
        return {
            'commit_count': commit_count,
            'lines_changed': lines_changed
        }
        
    except Exception as e:
        print(f"  Error getting diff stats: {e}")
        return {
            'commit_count': 0,
            'lines_changed': 0
        }

def track_customizations():
    """Track customizations across all forked repositories."""
    customization_data = {
        'last_updated': datetime.now().isoformat(),
        'repositories': {}
    }
    
    # Process each tier directory
    tiers = ['tier1', 'tier2', 'tier3', 'tier4']
    
    for tier in tiers:
        tier_dir = os.path.join(FORKS_DIR, tier)
        
        if not os.path.exists(tier_dir):
            print(f"Tier directory {tier_dir} does not exist, skipping...")
            continue
            
        print(f"\nTracking customizations in {tier}...")
        
        # Get all repository directories
        repo_dirs = [d for d in os.listdir(tier_dir) 
                    if os.path.isdir(os.path.join(tier_dir, d))]
        
        for repo_dir in repo_dirs:
            repo_path = os.path.join(tier_dir, repo_dir)
            print(f"  Tracking {repo_dir}...")
            
            # Get customization stats
            stats = get_git_diff_stats(repo_path)
            
            customization_data['repositories'][repo_dir] = {
                'tier': tier,
                'commits_ahead': stats['commit_count'],
                'lines_changed': stats['lines_changed'],
                'last_checked': datetime.now().isoformat()
            }
    
    # Save tracking data
    with open(CUSTOMIZATION_TRACKING_FILE, 'w', encoding='utf-8') as f:
        json.dump(customization_data, f, indent=2)
    
    print(f"\n[OK] Customization tracking data saved to {CUSTOMIZATION_TRACKING_FILE}")

if __name__ == "__main__":
    track_customizations()
