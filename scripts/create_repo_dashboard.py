#!/usr/bin/env python3
"""
Script to create a repository management dashboard.
"""

import os
import json
import subprocess
from datetime import datetime
from pathlib import Path

# Configuration
WORKSPACE_ROOT = r"c:\Users\Vincent_Pereira\Projects\Algo_Trading_Projects\Trae\Algorithmic Trading System"
FORKS_DIR = os.path.join(WORKSPACE_ROOT, "forks")
DEPENDENCIES_FILE = os.path.join(WORKSPACE_ROOT, "services", "dependency_management_service", "dependencies.json")
DASHBOARD_DIR = os.path.join(WORKSPACE_ROOT, "monitoring")

def load_dependencies():
    """Load the dependencies from the JSON file."""
    with open(DEPENDENCIES_FILE, 'r') as f:
        return json.load(f)

def get_repo_status(repo_path):
    """Get the status of a repository."""
    try:
        # Change to repository directory
        original_dir = os.getcwd()
        os.chdir(repo_path)
        
        # Get current branch
        result = subprocess.run(['git', 'branch', '--show-current'], 
                              capture_output=True, text=True)
        current_branch = result.stdout.strip() or "Unknown"
        
        # Get last commit date
        result = subprocess.run(['git', 'log', '-1', '--format=%cd', '--date=short'], 
                              capture_output=True, text=True)
        last_commit = result.stdout.strip() or "Unknown"
        
        # Check if repository has upstream
        result = subprocess.run(['git', 'remote', 'get-url', 'upstream'], 
                              capture_output=True, text=True)
        has_upstream = result.returncode == 0
        
        # Get commit count ahead/behind
        if has_upstream:
            result = subprocess.run(['git', 'rev-list', '--count', 'HEAD..upstream/main'], 
                                  capture_output=True, text=True)
            behind = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
            
            result = subprocess.run(['git', 'rev-list', '--count', 'upstream/main..HEAD'], 
                                  capture_output=True, text=True)
            ahead = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
        else:
            ahead, behind = 0, 0
        
        os.chdir(original_dir)
        
        return {
            'branch': current_branch,
            'last_commit': last_commit,
            'ahead': ahead,
            'behind': behind,
            'has_upstream': has_upstream,
            'status': 'synced' if ahead == 0 and behind == 0 else 'needs_sync' if behind > 0 else 'ahead'
        }
        
    except Exception as e:
        print(f"  Error getting repo status: {e}")
        return {
            'branch': 'Unknown',
            'last_commit': 'Unknown',
            'ahead': 0,
            'behind': 0,
            'has_upstream': False,
            'status': 'error'
        }

def create_dashboard():
    """Create a repository management dashboard."""
    # Load dependencies
    deps_data = load_dependencies()
    
    # Create dashboard HTML
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Repository Management Dashboard</title>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background-color: #f5f5f5;
        }
        .header { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            padding: 20px; 
            border-radius: 10px; 
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .stats-container { 
            display: flex; 
            justify-content: space-between; 
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .stat-card { 
            background: white; 
            padding: 20px; 
            border-radius: 8px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            flex: 1;
            margin: 5px;
            min-width: 200px;
            text-align: center;
        }
        .stat-number { 
            font-size: 2em; 
            font-weight: bold; 
            color: #667eea;
        }
        .tier-section { 
            background: white; 
            margin-bottom: 20px; 
            border-radius: 8px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .tier-header { 
            background-color: #f8f9fa; 
            padding: 15px 20px; 
            font-size: 1.2em; 
            font-weight: bold;
            border-bottom: 1px solid #eee;
        }
        .repo-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); 
            gap: 15px;
            padding: 20px;
        }
        .repo-card { 
            border: 1px solid #eee; 
            border-radius: 8px; 
            padding: 15px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .repo-card:hover { 
            transform: translateY(-2px); 
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        .repo-name { 
            font-weight: bold; 
            font-size: 1.1em; 
            margin-bottom: 8px;
            color: #333;
        }
        .repo-info { 
            font-size: 0.9em; 
            color: #666; 
            margin: 3px 0;
        }
        .status-indicator { 
            display: inline-block; 
            width: 10px; 
            height: 10px; 
            border-radius: 50%; 
            margin-right: 8px;
        }
        .status-synced { background-color: #28a745; }
        .status-needs_sync { background-color: #ffc107; }
        .status-ahead { background-color: #17a2b8; }
        .status-error { background-color: #dc3545; }
        .filter-bar { 
            margin-bottom: 20px; 
            display: flex; 
            gap: 10px;
        }
        .filter-btn { 
            padding: 8px 16px; 
            background: #e9ecef; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer;
        }
        .filter-btn.active { 
            background: #667eea; 
            color: white;
        }
        @media (max-width: 768px) {
            .stats-container { 
                flex-direction: column;
            }
            .repo-grid { 
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Repository Management Dashboard</h1>
        <p>Monitoring and managing all forked repositories</p>
    </div>
    
    <div class="stats-container">
        <div class="stat-card">
            <div class="stat-number">65</div>
            <div>Total Repositories</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">10</div>
            <div>Tier 1 Critical</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">19</div>
            <div>Tier 2 Important</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">11</div>
            <div>Tier 3 Supporting</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">25</div>
            <div>Tier 4 Infrastructure</div>
        </div>
    </div>
    
    <div class="filter-bar">
        <button class="filter-btn active" onclick="filterRepos('all')">All</button>
        <button class="filter-btn" onclick="filterRepos('synced')">Synced</button>
        <button class="filter-btn" onclick="filterRepos('needs_sync')">Needs Sync</button>
        <button class="filter-btn" onclick="filterRepos('ahead')">Ahead</button>
    </div>
"""

    # Process each tier
    tier_mapping = {
        'tier1': 'Tier 1: Critical Dependencies',
        'tier2': 'Tier 2: Important Dependencies', 
        'tier3': 'Tier 3: Supporting Dependencies',
        'tier4': 'Tier 4: Infrastructure Dependencies'
    }
    
    total_repos = 0
    synced_repos = 0
    needs_sync_repos = 0
    ahead_repos = 0
    
    for tier_key, tier_title in tier_mapping.items():
        html_content += f"""    <div class="tier-section">
        <div class="tier-header">{tier_title}</div>
        <div class="repo-grid">
"""
        
        tier_deps = deps_data['tiers'][tier_key]['dependencies']
        tier_dir = os.path.join(FORKS_DIR, tier_key.replace('tier', 'tier'))
        
        for dep in tier_deps:
            repo_name = dep['name']
            total_repos += 1
            
            # Try to get repo status
            normalized_name = repo_name.lower().replace(' ', '-').replace('.', '-')
            repo_path = os.path.join(tier_dir, normalized_name)
            
            # Check if repository exists
            if not os.path.exists(repo_path):
                repo_path = os.path.join(tier_dir, repo_name)
            
            if os.path.exists(repo_path):
                status = get_repo_status(repo_path)
                
                # Update counters
                if status['status'] == 'synced':
                    synced_repos += 1
                elif status['status'] == 'needs_sync':
                    needs_sync_repos += 1
                elif status['status'] == 'ahead':
                    ahead_repos += 1
                
                # Add repo card
                status_class = f"status-{status['status']}"
                status_text = status['status'].replace('_', ' ').title()
                
                html_content += f"""            <div class="repo-card" data-status="{status['status']}">
                <div class="repo-name">
                    <span class="status-indicator {status_class}"></span>
                    {repo_name}
                </div>
                <div class="repo-info">Branch: {status['branch']}</div>
                <div class="repo-info">Last commit: {status['last_commit']}</div>
                <div class="repo-info">Status: {status_text}</div>
"""
                
                if status['ahead'] > 0 or status['behind'] > 0:
                    html_content += f"""                <div class="repo-info">Commits: +{status['ahead']}/-{status['behind']}</div>
"""
                
                html_content += "            </div>\n"
            else:
                # Repo not found
                html_content += f"""            <div class="repo-card" data-status="error">
                <div class="repo-name">
                    <span class="status-indicator status-error"></span>
                    {repo_name}
                </div>
                <div class="repo-info">Status: Repository not found</div>
            </div>
"""
        
        html_content += "        </div>\n    </div>\n\n"
    
    # Add JavaScript for filtering
    html_content += """    <script>
        function filterRepos(status) {
            // Update active button
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // Filter repositories
            const repos = document.querySelectorAll('.repo-card');
            repos.forEach(repo => {
                if (status === 'all' || repo.dataset.status === status) {
                    repo.style.display = 'block';
                } else {
                    repo.style.display = 'none';
                }
            });
        }
    </script>
</body>
</html>
"""
    
    # Save dashboard
    dashboard_path = os.path.join(DASHBOARD_DIR, "repository_dashboard.html")
    os.makedirs(DASHBOARD_DIR, exist_ok=True)
    
    with open(dashboard_path, 'w') as f:
        f.write(html_content)
    
    print(f"Repository management dashboard saved to {dashboard_path}")
    
    # Also create a summary report
    summary_content = f"""# Repository Management Dashboard Summary

## Overview
This dashboard provides a centralized view of all forked repositories and their current status.

## Statistics
- **Total Repositories**: {total_repos}
- **Synced Repositories**: {synced_repos}
- **Needs Sync**: {needs_sync_repos}
- **Ahead of Upstream**: {ahead_repos}
- **Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Access
The dashboard can be accessed at: {dashboard_path}

## Features
1. Real-time status monitoring
2. Filtering by repository status
3. Commit history tracking
4. Sync status visualization
5. Tier-based organization

## Maintenance
This dashboard should be updated regularly to reflect the current state of all repositories.
"""
    
    summary_path = os.path.join(DASHBOARD_DIR, "repository_dashboard_summary.md")
    with open(summary_path, 'w') as f:
        f.write(summary_content)
    
    print(f"Dashboard summary saved to {summary_path}")

if __name__ == "__main__":
    create_dashboard()
    print("\n✅ Repository management dashboard created successfully!")