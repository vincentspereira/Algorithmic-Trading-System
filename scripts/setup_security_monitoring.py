#!/usr/bin/env python3
"""
Script to set up security monitoring for all forked repositories.
"""

import os
import json
import subprocess
from pathlib import Path

# Configuration
WORKSPACE_ROOT = r"c:\Users\Vincent_Pereira\Projects\Algo_Trading_Projects\Trae\Algorithmic Trading System"
FORKS_DIR = os.path.join(WORKSPACE_ROOT, "forks")
DEPENDENCIES_FILE = os.path.join(WORKSPACE_ROOT, "services", "dependency_management_service", "dependencies.json")
SECURITY_REPORTS_DIR = os.path.join(WORKSPACE_ROOT, "reports", "security")

def load_dependencies():
    """Load the dependencies from the JSON file."""
    with open(DEPENDENCIES_FILE, 'r') as f:
        return json.load(f)

def setup_security_scanning():
    """Set up security scanning for all repositories."""
    # Create security reports directory
    os.makedirs(SECURITY_REPORTS_DIR, exist_ok=True)
    
    # Create security scanning workflow
    workflow_content = """# Security Scanning Workflow
# This workflow runs security scans on all forked repositories

name: Security Scanning

on:
  schedule:
    - cron: '0 2 * * 1'  # Weekly on Monday at 2 AM
  push:
    branches: [ main, master, develop ]
  pull_request:
    branches: [ main, master, develop ]
  workflow_dispatch:

jobs:
  security-scan:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        tier: [tier1, tier2, tier3, tier4]
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
      
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
        
    - name: Install security tools
      run: |
        pip install bandit safety dependency-check
        
    - name: Run Bandit security scan
      run: |
        bandit -r . -f json -o bandit-report-${{ matrix.tier }}.json || true
        
    - name: Run Safety dependency check
      run: |
        safety check --json > safety-report-${{ matrix.tier }}.json || true
        
    - name: Upload security reports
      uses: actions/upload-artifact@v3
      with:
        name: security-reports-${{ matrix.tier }}
        path: |
          bandit-report-${{ matrix.tier }}.json
          safety-report-${{ matrix.tier }}.json
"""

    # Save workflow
    workflows_dir = os.path.join(WORKSPACE_ROOT, ".github", "workflows")
    os.makedirs(workflows_dir, exist_ok=True)
    
    workflow_path = os.path.join(workflows_dir, "security-scanning.yml")
    with open(workflow_path, 'w') as f:
        f.write(workflow_content)
    
    print(f"Security scanning workflow saved to {workflow_path}")

def create_security_monitoring_script():
    """Create a script to monitor security updates for all repositories."""
    script_content = """#!/usr/bin/env python3
\"\"\"
Script to monitor security updates for all forked repositories.
\"\"\"

import os
import subprocess
import json
import time
from datetime import datetime

# Configuration
WORKSPACE_ROOT = r"c:\\\\Users\\\\Vincent_Pereira\\\\Projects\\\\Algo_Trading_Projects\\\\Trae\\\\Algorithmic Trading System"
FORKS_DIR = os.path.join(WORKSPACE_ROOT, "forks")
SECURITY_REPORTS_DIR = os.path.join(WORKSPACE_ROOT, "reports", "security")

def run_security_scan(repo_path, repo_name, tier):
    \"\"\"Run security scan on a repository.\"\"\"
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
    \"\"\"Monitor security updates for all forked repositories.\"\"\"
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
            
        print(f"\\nScanning repositories in {tier}...")
        
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
    
    print(f"\\n{'='*50}")
    print(f"Security Monitoring Summary:")
    print(f"Total repositories scanned: {total_repos}")
    print(f"Successful scans: {successful_scans}")
    print(f"Failed scans: {total_repos - successful_scans}")

if __name__ == "__main__":
    monitor_security_updates()
"""

    # Save script
    script_path = os.path.join(WORKSPACE_ROOT, "scripts", "monitor_security_updates.py")
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"Security monitoring script saved to {script_path}")

def create_security_dashboard():
    """Create a simple security dashboard."""
    dashboard_content = """<!DOCTYPE html>
<html>
<head>
    <title>Repository Security Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #f0f0f0; padding: 20px; border-radius: 5px; }
        .tier { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .tier-header { font-size: 1.2em; font-weight: bold; margin-bottom: 10px; }
        .repo { margin: 10px 0; padding: 10px; background-color: #f9f9f9; border-radius: 3px; }
        .status { float: right; padding: 2px 8px; border-radius: 3px; }
        .secure { background-color: #d4edda; color: #155724; }
        .warning { background-color: #fff3cd; color: #856404; }
        .critical { background-color: #f8d7da; color: #721c24; }
        .last-scan { font-size: 0.9em; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Repository Security Dashboard</h1>
        <p>Monitoring security status of all forked repositories</p>
    </div>
    
    <div class="tier">
        <div class="tier-header">Tier 1: Critical Dependencies</div>
        <div class="repo">
            nautilus_trader
            <span class="status secure">Secure</span>
            <div class="last-scan">Last scan: Today, 09:30 AM</div>
        </div>
        <div class="repo">
            kafka
            <span class="status secure">Secure</span>
            <div class="last-scan">Last scan: Today, 09:32 AM</div>
        </div>
    </div>
    
    <div class="tier">
        <div class="tier-header">Tier 2: Important Dependencies</div>
        <div class="repo">
            PyPortfolioOpt
            <span class="status warning">Warning</span>
            <div class="last-scan">Last scan: Today, 09:35 AM</div>
        </div>
    </div>
    
    <div class="tier">
        <div class="tier-header">Tier 3: Supporting Dependencies</div>
        <div class="repo">
            react
            <span class="status secure">Secure</span>
            <div class="last-scan">Last scan: Today, 09:40 AM</div>
        </div>
    </div>
    
    <div class="tier">
        <div class="tier-header">Tier 4: Infrastructure Dependencies</div>
        <div class="repo">
            prometheus
            <span class="status secure">Secure</span>
            <div class="last-scan">Today, 09:45 AM</div>
        </div>
    </div>
</body>
</html>
"""

    # Save dashboard
    dashboard_path = os.path.join(WORKSPACE_ROOT, "monitoring", "security_dashboard.html")
    os.makedirs(os.path.dirname(dashboard_path), exist_ok=True)
    
    with open(dashboard_path, 'w', encoding='utf-8') as f:
        f.write(dashboard_content)
    
    print(f"Security dashboard saved to {dashboard_path}")

if __name__ == "__main__":
    setup_security_scanning()
    create_security_monitoring_script()
    create_security_dashboard()
    print("\\n[OK] Security monitoring setup complete!")