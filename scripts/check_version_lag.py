#!/usr/bin/env python3

import argparse
import json
import sys
import os
from pathlib import Path
import requests
from packaging import version

def check_version_lag(deps, token):
    """Check version lag for each dependency"""
    results = []
    
    for dep in deps:
        if 'repository' not in dep:
            continue
            
        repo_url = dep['repository']
        if 'github.com' not in repo_url:
            continue
            
        # Extract owner/repo from URL
        _, _, _, owner, repo = repo_url.rstrip('/').split('/')
        
        # Get latest release or tag
        headers = {'Authorization': f'token {token}'}
        
        # Try releases first
        api_url = f'https://api.github.com/repos/{owner}/{repo}/releases/latest'
        try:
            resp = requests.get(api_url, headers=headers)
            if resp.status_code == 404:
                # If no releases, try tags
                api_url = f'https://api.github.com/repos/{owner}/{repo}/tags'
                resp = requests.get(api_url, headers=headers)
                resp.raise_for_status()
                # Find first tag that looks like a version
                for tag in resp.json():
                    tag_name = tag['name'].lstrip('v')
                    try:
                        version.parse(tag_name)
                        latest = tag_name
                        break
                    except:
                        continue
                if 'latest' not in locals():
                    raise Exception("No valid version tag found")
            else:
                resp.raise_for_status()
                latest = resp.json()['tag_name'].lstrip('v')
            current = dep['version'].lstrip('v')
            
            lag = version.parse(latest) > version.parse(current)
            major_lag = version.parse(latest).major > version.parse(current).major
            
            results.append({
                'name': dep['name'],
                'current_version': current,
                'latest_version': latest,
                'status': 'red' if major_lag else ('yellow' if lag else 'green')
            })
        except Exception as e:
            print(f"Error checking {dep['name']}: {e}")
            results.append({
                'name': dep['name'],
                'error': str(e),
                'status': 'red'
            })
    
    return results

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--tier', type=int, required=True)
    parser.add_argument('--token', required=True)
    args = parser.parse_args()
    
    # Load dependencies
    deps_file = Path(__file__).parent.parent / 'dependency_management' / 'dependencies.json'
    with open(deps_file) as f:
        config = json.load(f)
    
    deps = config['tiers'][f'tier{args.tier}']['dependencies']
    results = check_version_lag(deps, args.token)
    
    # Set output for GitHub Actions
    with open(os.getenv('GITHUB_OUTPUT', 'version_status.json'), 'w') as f:
        json.dump(results, f)
