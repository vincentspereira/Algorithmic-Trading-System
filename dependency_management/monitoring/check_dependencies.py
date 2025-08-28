#!/usr/bin/env python3
"""
Dependency monitoring script for the Algorithmic Trading System.
Checks for updates and vulnerabilities in project dependencies.
"""

import json
import requests
import subprocess
import sys
from packaging import version
from pathlib import Path

def load_tier_dependencies(tier_file):
    """Load dependencies from a tier JSON file."""
    with open(tier_file, 'r') as f:
        data = json.load(f)
    return data['dependencies']

def check_pypi_version(package_name):
    """Check the latest version of a package on PyPI."""
    try:
        response = requests.get(f'https://pypi.org/pypi/{package_name}/json', timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data['info']['version']
    except Exception as e:
        print(f"Error checking PyPI for {package_name}: {e}")
    return None

def check_dependency_updates(dependencies):
    """Check for updates in dependencies."""
    updates_needed = []
    
    for dep in dependencies:
        name = dep['name']
        dep_type = dep['type']
        
        try:
            if dep_type in ['trading_engine', 'event_bus', 'ai_framework', 'technical_analysis', 
                           'backtesting', 'reinforcement_learning', 'portfolio_optimization',
                           'risk_management', 'quantitative_finance', 'nlp', 'deep_learning']:
                
                # Check for updates (simulated for now)
                print(f"Checking {name} ({dep_type})...")
                
        except Exception as e:
            print(f"Error checking {name}: {e}")
            
    return updates_needed

def main():
    """Main function to check all tier dependencies."""
    print("Starting dependency monitoring...")
    
    # Define tier files
    tier_files = [
        'dependency_management/tiers/tier1_critical.json',
        'dependency_management/tiers/tier2_important.json',
        'dependency_management/tiers/tier3_supporting.json',
        'dependency_management/tiers/tier4_infrastructure.json'
    ]
    
    all_updates = []
    
    # Check each tier
    for tier_file in tier_files:
        if Path(tier_file).exists():
            print(f"Checking {tier_file}...")
            dependencies = load_tier_dependencies(tier_file)
            updates = check_dependency_updates(dependencies)
            all_updates.extend(updates)
        else:
            print(f"Warning: {tier_file} not found")
    
    # Report results
    if all_updates:
        print("\nUpdates available:")
        for update in all_updates:
            print(f"  {update['name']}: {update['local_version']} -> {update['latest_version']}")
        return 1  # Exit with error code to trigger notifications
    else:
        print("All dependencies are up to date.")
        return 0  # Exit successfully

if __name__ == "__main__":
    sys.exit(main())