#!/usr/bin/env python3

import argparse
import json
import os
from pathlib import Path
import requests
import datetime

def check_upstream_activity(deps, token):
    """Check last commit date for each dependency"""
    results = []
    now = datetime.datetime.now(datetime.timezone.utc)
    
    for dep in deps:
        if 'repository' not in dep:
            continue
            
        repo_url = dep['repository']
        if 'github.com' not in repo_url:
            continue
            
        # Extract owner/repo from URL
        _, _, _, owner, repo = repo_url.rstrip('/').split('/')
        
        # Get latest commit
        headers = {'Authorization': f'token {token}'}
        api_url = f'https://api.github.com/repos/{owner}/{repo}/commits'
        
        try:
            resp = requests.get(api_url, headers=headers)
            resp.raise_for_status()
            last_commit = datetime.datetime.fromisoformat(
                resp.json()[0]['commit']['committer']['date'].replace('Z', '+00:00')
            )
            
            months_since = (now - last_commit).days / 30.44  # Average month length
            
            results.append({
                'name': dep['name'],
                'last_commit': last_commit.isoformat(),
                'months_since': round(months_since, 1),
                'status': 'red' if months_since > 12 else ('yellow' if months_since > 6 else 'green')
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
    results = check_upstream_activity(deps, args.token)
    
    # Set output for GitHub Actions
    with open(os.getenv('GITHUB_OUTPUT', 'activity_status.json'), 'w') as f:
        json.dump(results, f)
