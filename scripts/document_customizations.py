#!/usr/bin/env python3
"""
Script to document customizations for each forked repository.
"""

import os
import json
from pathlib import Path

# Configuration
WORKSPACE_ROOT = r"c:\Users\Vincent_Pereira\Projects\Algo_Trading_Projects\Trae\Algorithmic Trading System"
FORKS_DIR = os.path.join(WORKSPACE_ROOT, "forks")
DEPENDENCIES_FILE = os.path.join(WORKSPACE_ROOT, "services", "dependency_management_service", "dependencies.json")
CUSTOMIZATION_DOCS_DIR = os.path.join(WORKSPACE_ROOT, "docs", "customizations")

def load_dependencies():
    """Load the dependencies from the JSON file."""
    with open(DEPENDENCIES_FILE, 'r') as f:
        return json.load(f)

def create_customization_documentation():
    """Create customization documentation for all repositories."""
    # Create customization docs directory
    os.makedirs(CUSTOMIZATION_DOCS_DIR, exist_ok=True)
    
    # Load dependencies
    deps_data = load_dependencies()
    
    # Create main customization index
    index_content = """# Repository Customization Documentation

## Overview
This documentation tracks customizations made to each forked repository for the Algorithmic Trading System.

## Repository Customizations by Tier

"""
    
    # Process each tier
    tier_mapping = {
        'tier1': 'Tier 1: Critical Dependencies',
        'tier2': 'Tier 2: Important Dependencies', 
        'tier3': 'Tier 3: Supporting Dependencies',
        'tier4': 'Tier 4: Infrastructure Dependencies'
    }
    
    total_customizations = 0
    
    for tier_key, tier_title in tier_mapping.items():
        index_content += f"## {tier_title}\n\n"
        
        tier_deps = deps_data['tiers'][tier_key]['dependencies']
        for dep in tier_deps:
            repo_name = dep['name']
            customizations = dep.get('customizations', [])
            
            # Add to index
            index_content += f"- [{repo_name}](./{repo_name.replace(' ', '_').replace('.', '_')}.md)"
            if customizations:
                index_content += f" - {len(customizations)} customizations\n"
                total_customizations += len(customizations)
            else:
                index_content += " - No customizations\n"
            
            # Create individual customization document
            repo_doc_content = f"""# {repo_name} Customizations

## Repository Information
- **Upstream**: {dep['repository']}
- **Fork**: {dep.get('fork', 'Not specified')}
- **Tier**: {tier_title}

## Customizations
"""
            
            if customizations:
                for i, customization in enumerate(customizations, 1):
                    repo_doc_content += f"{i}. {customization}\n"
            else:
                repo_doc_content += "No customizations have been made to this repository.\n"
            
            # Add tracking information
            repo_doc_content += f"""

## Tracking Information
- **Last Updated**: {deps_data.get('last_updated', 'Unknown')}
- **Version**: {deps_data.get('version', 'Unknown')}

## Change History
| Date | Change | Author |
|------|--------|--------|
| {deps_data.get('last_updated', 'Unknown')} | Initial documentation | System |
"""
            
            # Save individual document
            doc_filename = f"{repo_name.replace(' ', '_').replace('.', '_')}.md"
            doc_path = os.path.join(CUSTOMIZATION_DOCS_DIR, doc_filename)
            
            with open(doc_path, 'w', encoding='utf-8') as f:
                f.write(repo_doc_content)
        
        index_content += "\n"
    
    # Add summary
    index_content += f"""## Summary
- **Total Repositories**: 65
- **Total Customizations**: {total_customizations}
- **Last Updated**: {deps_data.get('last_updated', 'Unknown')}

## Maintenance
This documentation should be updated whenever customizations are made to any forked repository.
"""
    
    # Save index
    index_path = os.path.join(CUSTOMIZATION_DOCS_DIR, "README.md")
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_content)
    
    print(f"Customization documentation saved to {index_path}")
    print(f"Individual repository documentation saved to {CUSTOMIZATION_DOCS_DIR}")

def create_customization_tracking_script():
    """Create a script to track customizations in real-time."""
    script_content = """#!/usr/bin/env python3
\"\"\"
Script to track customizations made to forked repositories.
\"\"\"

import os
import json
import subprocess
from datetime import datetime
from pathlib import Path

# Configuration
WORKSPACE_ROOT = r"c:\\\\Users\\\\Vincent_Pereira\\\\Projects\\\\Algo_Trading_Projects\\\\Trae\\\\Algorithmic Trading System"
FORKS_DIR = os.path.join(WORKSPACE_ROOT, "forks")
CUSTOMIZATION_TRACKING_FILE = os.path.join(WORKSPACE_ROOT, "dependency_management", "customization_tracking.json")

def get_git_diff_stats(repo_path):
    \"\"\"Get statistics about changes in a repository.\"\"\"
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
            for line in result.stdout.split('\\n'):
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
    \"\"\"Track customizations across all forked repositories.\"\"\"
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
            
        print(f"\\nTracking customizations in {tier}...")
        
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
    
    print(f"\\n[OK] Customization tracking data saved to {CUSTOMIZATION_TRACKING_FILE}")

if __name__ == "__main__":
    track_customizations()
"""

    # Save script
    script_path = os.path.join(WORKSPACE_ROOT, "scripts", "track_customizations.py")
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"Customization tracking script saved to {script_path}")

if __name__ == "__main__":
    create_customization_documentation()
    create_customization_tracking_script()
    print("\\n[OK] Customization documentation setup complete!")