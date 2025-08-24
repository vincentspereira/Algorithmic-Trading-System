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

def check_npm_version(package_name):
    """Check the latest version of a package on npm."""
    try:
        response = requests.get(f'https://registry.npmjs.org/{package_name}', timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data['dist-tags']['latest']
    except Exception as e:
        print(f"Error checking npm for {package_name}: {e}")
    return None

def get_local_python_version(package_name):
    """Get the locally installed version of a Python package."""
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'show', package_name],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.startswith('Version:'):
                    return line.split(':', 1)[1].strip()
    except Exception as e:
        print(f"Error getting local version for {package_name}: {e}")
    return None

def get_local_npm_version(package_name):
    """Get the locally installed version of an npm package."""
    try:
        result = subprocess.run(
            ['npm', 'list', package_name, 'version'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            # Parse npm output to extract version
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if package_name in line and '@' in line:
                    return line.split('@')[-1]
    except Exception as e:
        print(f"Error getting local npm version for {package_name}: {e}")
    return None

def check_dependency_updates(dependencies):
    """Check for updates in dependencies."""
    updates_needed = []
    
    for dep in dependencies:
        name = dep['name']
        dep_type = dep['type']
        
        try:
            if dep_type in ['trading_engine', 'event_bus', 'ai_framework', 'technical_analysis', 
                           'backtesting', 'reinforcement_learning', 'anomaly_detection',
                           'portfolio_optimization', 'risk_management', 'forecasting',
                           'quantitative_finance', 'nlp', 'deep_learning', 'explainable_ai',
                           'document_processing', 'vector_database', 'database',
                           'monitoring', 'distributed_tracing', 'log_aggregation',
                           'feature_flags', 'data_lake', 'security_scanning']:
                
                # Python package
                local_version = get_local_python_version(name)
                if local_version:
                    latest_version = check_pypi_version(name)
                    if latest_version and version.parse(latest_version) > version.parse(local_version):
                        updates_needed.append({
                            'name': name,
                            'local_version': local_version,
                            'latest_version': latest_version,
                            'type': 'python'
                        })
                        
            elif dep_type in ['no_code', 'visualization']:
                # npm package
                local_version = get_local_npm_version(name)
                if local_version:
                    latest_version = check_npm_version(name)
                    if latest_version and version.parse(latest_version) > version.parse(local_version):
                        updates_needed.append({
                            'name': name,
                            'local_version': local_version,
                            'latest_version': latest_version,
                            'type': 'npm'
                        })
        except Exception as e:
            print(f"Error checking {name}: {e}")
            
    return updates_needed

def main():
    """Main function to check all tier dependencies."""
    print("Starting dependency monitoring...")
    
    # Define tier files
    tier_files = [
        'dependency_management/tiers/tier1_critical.json',
        'dependency_management/tiers/tier2_important.json'
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