#!/usr/bin/env python3
"""
Script to document and configure branch protection rules for all forked repositories.
"""

import os
import json

# Configuration
WORKSPACE_ROOT = r"c:\Users\Vincent_Pereira\Projects\Algo_Trading_Projects\Trae\Algorithmic Trading System"
FORKS_DIR = os.path.join(WORKSPACE_ROOT, "forks")
DEPENDENCIES_FILE = os.path.join(WORKSPACE_ROOT, "services", "dependency_management_service", "dependencies.json")

def load_dependencies():
    """Load the dependencies from the JSON file."""
    with open(DEPENDENCIES_FILE, 'r') as f:
        return json.load(f)

def generate_branch_protection_policy():
    """Generate branch protection policy documentation."""
    policy_content = """# Branch Protection Policy for Forked Repositories

## Overview
This document outlines the branch protection rules that should be applied to all forked repositories to ensure code quality and security.

## Standard Branch Protection Rules

### Main/Branch Protection Rules
1. **Require pull request reviews before merging**
   - Require at least 1 approved review
   - Dismiss stale pull request approvals when new commits are pushed
   - Require review from Code Owners (where applicable)

2. **Require status checks to pass before merging**
   - Require branches to be up to date before merging
   - Status checks:
     - Continuous Integration (CI) builds
     - Security scanning
     - Code quality checks
     - Unit tests

3. **Branch name patterns**
   - Main branches: `main`, `master`, `develop`
   - Feature branches: `feature/*`, `feat/*`
   - Bug fix branches: `fix/*`, `bugfix/*`
   - Release branches: `release/*`
   - Hotfix branches: `hotfix/*`

4. **Restrictions**
   - Restrict who can push to matching branches
   - Allow force pushes (disabled for main branches)
   - Allow deletions (disabled for main branches)

## Implementation Instructions

### For GitHub Repositories:

1. Navigate to the repository settings
2. Go to "Branches" section
3. Under "Branch protection rules", click "Add rule"
4. Set the branch name pattern (e.g., `main`, `master`)
5. Configure the following settings:
   - Check "Require pull request reviews before merging"
   - Check "Require status checks to pass before merging"
   - Check "Require branches to be up to date before merging"
   - Check "Include administrators" (recommended)
   - Check "Restrict who can push to matching branches"
   - Uncheck "Allow force pushes" for main branches
   - Uncheck "Allow deletions" for main branches

### Required Status Checks by Tier:

#### Tier 1 (Critical Dependencies):
- CI/CD Pipeline
- Security Scan (Bandit, Snyk)
- Code Quality (SonarQube)
- Unit Tests (100% coverage required)

#### Tier 2 (Important Dependencies):
- CI/CD Pipeline
- Security Scan (Bandit)
- Code Quality (SonarQube)
- Unit Tests (90% coverage required)

#### Tier 3 (Supporting Dependencies):
- CI/CD Pipeline
- Security Scan (Bandit)
- Unit Tests (80% coverage required)

#### Tier 4 (Infrastructure Dependencies):
- CI/CD Pipeline
- Security Scan (Bandit)
- Unit Tests (70% coverage required)

## Automation

To automate branch protection rule application, use the GitHub API or GitHub CLI:

```bash
# Example using GitHub CLI
gh api \
  --method PUT \
  -H "Accept: application/vnd.github.v3+json" \
  /repos/{owner}/{repo}/branches/{branch}/protection \
  -f required_status_checks='{"strict": true, "contexts": ["continuous-integration/jenkins"]}' \
  -f enforce_admins=true \
  -f required_pull_request_reviews='{"dismiss_stale_reviews": true}' \
  -f restrictions=null
```

## Monitoring

Branch protection rules should be monitored regularly to ensure they remain effective:
- Weekly review of branch protection configurations
- Alerting on any changes to protection rules
- Periodic audit of bypassed protection rules
"""

    # Save policy document
    policy_path = os.path.join(WORKSPACE_ROOT, "docs", "branch_protection_policy.md")
    os.makedirs(os.path.dirname(policy_path), exist_ok=True)
    
    with open(policy_path, 'w') as f:
        f.write(policy_content)
    
    print(f"Branch protection policy saved to {policy_path}")

def generate_repository_list():
    """Generate a list of all repositories with their tiers."""
    # Load dependencies
    deps_data = load_dependencies()
    
    # Generate repository list
    repo_list_content = "# Repository Branch Protection Requirements\n\n"
    repo_list_content += "This document lists all repositories and their required branch protection configurations.\n\n"
    
    # Process each tier
    tier_mapping = {
        'tier1': 'Tier 1: Critical Dependencies',
        'tier2': 'Tier 2: Important Dependencies', 
        'tier3': 'Tier 3: Supporting Dependencies',
        'tier4': 'Tier 4: Infrastructure Dependencies'
    }
    
    for tier_key, tier_title in tier_mapping.items():
        repo_list_content += f"## {tier_title}\n\n"
        
        tier_deps = deps_data['tiers'][tier_key]['dependencies']
        for dep in tier_deps:
            repo_name = dep['name']
            repo_url = dep['repository']
            fork_url = dep.get('fork', 'Not specified')
            
            repo_list_content += f"- **{repo_name}**\n"
            repo_list_content += f"  - Upstream: {repo_url}\n"
            repo_list_content += f"  - Fork: {fork_url}\n"
            repo_list_content += f"  - Protection Tier: {tier_title.split(':')[0]}\n\n"
    
    # Save repository list
    list_path = os.path.join(WORKSPACE_ROOT, "dependency_management", "repository_branch_protection_list.md")
    os.makedirs(os.path.dirname(list_path), exist_ok=True)
    
    with open(list_path, 'w') as f:
        f.write(repo_list_content)
    
    print(f"Repository branch protection list saved to {list_path}")

if __name__ == "__main__":
    generate_branch_protection_policy()
    generate_repository_list()
    print("\n✅ Branch protection documentation generated successfully!")