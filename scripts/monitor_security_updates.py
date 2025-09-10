#!/usr/bin/env python3
"""
Script to monitor security updates for all forked repositories.
"""

import os
import subprocess
import json
import time
from datetime import datetime

# Configuration
WORKSPACE_ROOT = r"c:\\Users\\Vincent_Pereira\\Projects\\Algo_Trading_Projects\\Trae\\Algorithmic Trading System"
FORKS_DIR = os.path.join(WORKSPACE_ROOT, "forks")
SECURITY_REPORTS_DIR = os.path.join(WORKSPACE_ROOT, "reports", "security")

def run_security_scan(repo_path, repo_name, tier):
    """Run security scan on a repository."""
    try:
        # Change to repository directory
        original_dir = os.getcwd()
        os.chdir(repo_path)
        
        # Create timestamp for reports
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Run Bandit scan
        bandit_report = os.path.join(SECURITY_REPORTS_DIR, f"{repo_name}_bandit_{timestamp}.json")
        try:
            subprocess.run([
                'bandit', '-r', '.', '-f', 'json', '-o', bandit_report
            ], check=True, capture_output=True)
            print(f"  [OK] Bandit scan completed for {repo_name}")
        except subprocess.CalledProcessError:
            print(f"  [WARNING] Bandit scan completed with warnings for {repo_name}")
        
        # Run Safety check (if requirements.txt exists)
        if os.path.exists("requirements.txt"):
            safety_report = os.path.join(SECURITY_REPORTS_DIR, f"{repo_name}_safety_{timestamp}.json")
            try:
                subprocess.run([
                    'safety', 'check', '--json', '-o', safety_report
                ], check=True, capture_output=True)
                print(f"  [OK] Safety check completed for {repo_name}")
            except subprocess.CalledProcessError:
                print(f"  [WARNING] Safety check completed with warnings for {repo_name}")
        
        os.chdir(original_dir)
        return True
        
    except Exception as e:
        print(f"  [ERROR] Error scanning {repo_name}: {e}")
        return False

def monitor_security_updates():
    """Monitor security updates for all forked repositories."""
    # Create security reports directory
    os.makedirs(SECURITY_REPORTS_DIR, exist_ok=True)
    
    # Process each tier directory
    tiers = ['tier1', 'tier2', 'tier3', 'tier4']
    total_repos = 0
    successful_scans = 0
    
    for tier in tiers:
        tier_dir = os.path.join(FORKS_DIR, tier)
        
        if not os.path.exists(tier_dir):
            print(f"Tier directory {tier_dir} does not exist, skipping...")
            continue
            
        print(f"\nScanning repositories in {tier}...")
        
        # Get all repository directories
        repo_dirs = [d for d in os.listdir(tier_dir) 
                    if os.path.isdir(os.path.join(tier_dir, d))]
        
        for repo_dir in repo_dirs:
            total_repos += 1
            repo_path = os.path.join(tier_dir, repo_dir)
            print(f"  Scanning {repo_dir}...")
            
            if run_security_scan(repo_path, repo_dir, tier):
                successful_scans += 1
            
            # Add delay to avoid overwhelming the system
            time.sleep(1)
    
    print(f"\n{'='*50}")
    print(f"Security Monitoring Summary:")
    print(f"Total repositories scanned: {total_repos}")
    print(f"Successful scans: {successful_scans}")
    print(f"Failed scans: {total_repos - successful_scans}")

if __name__ == "__main__":
    monitor_security_updates()
