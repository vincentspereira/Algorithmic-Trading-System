# Branch Protection Policy for Forked Repositories

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
gh api   --method PUT   -H "Accept: application/vnd.github.v3+json"   /repos/{owner}/{repo}/branches/{branch}/protection   -f required_status_checks='{"strict": true, "contexts": ["continuous-integration/jenkins"]}'   -f enforce_admins=true   -f required_pull_request_reviews='{"dismiss_stale_reviews": true}'   -f restrictions=null
```

## Monitoring

Branch protection rules should be monitored regularly to ensure they remain effective:
- Weekly review of branch protection configurations
- Alerting on any changes to protection rules
- Periodic audit of bypassed protection rules
