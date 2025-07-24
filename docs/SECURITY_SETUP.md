# Security Scan Setup and Configuration

This document provides instructions for setting up and using the security scanning tools in the Algorithmic Trading System.

## Overview

The project uses **Bandit** for Static Application Security Testing (SAST) to identify common security issues in Python code. The security scans are integrated with **pre-commit hooks** to automatically run before each commit.

## Prerequisites

- Python 3.11+ installed
- **Virtual environment activated** (see Development Environment Setup below)

⚠️ **CRITICAL**: Never install packages globally. Always use virtual environments or Docker containers.

## Development Environment Setup

**IMPORTANT**: Before installing any dependencies, set up a proper Python virtual environment to avoid installing packages globally on your system.

### Option 1: Use Provided Setup Scripts (Recommended)

```bash
# Linux/Mac
./scripts/setup_dev_env.sh

# Windows
.\scripts\setup_dev_env.bat
```

### Option 2: Manual Virtual Environment Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate.bat

# Verify you're in the virtual environment
which python  # Linux/Mac
where python   # Windows
# Should point to venv/bin/python or venv\Scripts\python.exe
```

## Installation and Setup

### 1. Install Dependencies

⚠️ **ENSURE VIRTUAL ENVIRONMENT IS ACTIVATED FIRST**

Install the required security tools and dependencies:

```bash
# Verify virtual environment is active (should show venv path)
echo $VIRTUAL_ENV  # Linux/Mac
echo %VIRTUAL_ENV%  # Windows

# Install from requirements.txt (includes bandit and pre-commit)
pip install -r nautilus_trader_engine/requirements.txt
```

### 2. Install Pre-commit Hooks

Set up pre-commit hooks to automatically run security scans before commits:

```bash
# Install pre-commit hooks
pre-commit install

# Verify installation
pre-commit --version
```

### 3. Run Initial Security Scan

Run an initial security scan to check the current codebase:

```bash
# Run pre-commit on all files (first time setup)
pre-commit run --all-files
```

## Manual Security Scanning

### Running Bandit Manually

You can run Bandit security scans manually at any time:

```bash
# Basic scan of entire project
bandit -r .

# Scan with detailed output
bandit -r . -f json -o security_report.json

# Scan specific directory
bandit -r nautilus_trader_engine/

# Scan with custom severity levels
bandit -r . -ll  # Low severity and above
bandit -r . -l   # Medium severity and above
bandit -r . -i   # High severity only
```

### Understanding Bandit Output

Bandit reports security issues with the following format:
- **Test ID**: Unique identifier for the security test (e.g., B101, B602)
- **Severity**: LOW, MEDIUM, or HIGH
- **Confidence**: LOW, MEDIUM, or HIGH
- **Description**: Explanation of the security issue
- **Location**: File path and line number

Example output:
```
>> Issue: [B101:assert_used] Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.
   Severity: Low   Confidence: High
   Location: ./nautilus_trader_engine/main.py:45
```

## Configuration

### Bandit Configuration

The `.pre-commit-config.yaml` file contains the Bandit configuration:

- **Recursive scan**: `-r .` scans all directories recursively
- **Custom format**: Provides detailed output with file paths and line numbers
- **Exclusions**: Automatically excludes test files, virtual environments, and setup files

### Customizing Security Rules

To customize Bandit rules, create a `.bandit` configuration file in the project root:

```yaml
# .bandit
exclude_dirs:
  - tests
  - venv
  - .venv
  - env
  - .env

skips:
  - B101  # Skip assert_used warnings
  - B601  # Skip shell injection warnings for specific cases

tests:
  - B102  # Enable exec_used test
  - B103  # Enable set_bad_file_permissions test
```

### Pre-commit Hook Customization

Modify `.pre-commit-config.yaml` to adjust the security scanning behavior:

```yaml
- id: bandit
  args: ['-r', '.', '--severity-level', 'medium']  # Only medium+ severity
  exclude: ^(tests/|docs/)  # Additional exclusions
```

## Integration with CI/CD

### GitHub Actions Integration

Add security scanning to your CI/CD pipeline:

```yaml
# .github/workflows/security.yml
name: Security Scan
on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install bandit
      - name: Run Bandit security scan
        run: bandit -r . -f json -o bandit-report.json
      - name: Upload security report
        uses: actions/upload-artifact@v3
        with:
          name: bandit-security-report
          path: bandit-report.json
```

## Common Security Issues and Fixes

### 1. Hardcoded Passwords (B105, B106)
**Issue**: Passwords or secrets in source code
**Fix**: Use environment variables or secure vaults

```python
# Bad
password = "hardcoded_password"

# Good
import os
password = os.getenv('DATABASE_PASSWORD')
```

### 2. SQL Injection (B608)
**Issue**: Dynamic SQL query construction
**Fix**: Use parameterized queries

```python
# Bad
query = f"SELECT * FROM users WHERE id = {user_id}"

# Good
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))
```

### 3. Shell Injection (B602, B603)
**Issue**: Using shell commands with user input
**Fix**: Use subprocess with shell=False

```python
# Bad
os.system(f"ls {user_input}")

# Good
import subprocess
subprocess.run(['ls', user_input], check=True)
```

## Troubleshooting

### Common Issues

1. **Pre-commit hook fails**: Ensure all dependencies are installed
2. **False positives**: Use inline comments to suppress specific warnings:
   ```python
   # nosec B101
   assert condition, "This is safe in our context"
   ```
3. **Performance issues**: Exclude large directories or files that don't need scanning

### Getting Help

- Bandit documentation: https://bandit.readthedocs.io/
- Pre-commit documentation: https://pre-commit.com/
- Security best practices: https://owasp.org/www-project-top-ten/

## Maintenance

### Regular Updates

Keep security tools updated:

```bash
# Update pre-commit hooks
pre-commit autoupdate

# Update Bandit
pip install --upgrade bandit
```

### Periodic Security Reviews

- Run full security scans monthly
- Review and address all HIGH severity issues immediately
- Evaluate MEDIUM severity issues for business impact
- Document any accepted risks with justification
## Environment Isolation and Security

### Why Virtual Environments Matter for Security

Using virtual environments is not just a best practice—it's a security requirement:

1. **Isolation**: Prevents conflicts between project dependencies
2. **Security**: Limits the scope of potentially vulnerable packages
3. **Reproducibility**: Ensures consistent environments across team members
4. **System Protection**: Prevents accidental system-wide package installations

### Production Deployment

For production environments, use Docker containers (already configured):

```bash
# Build and run with Docker (recommended for production)
docker-compose up -d

# This provides complete isolation and security
```

### Global Package Cleanup

If you suspect packages were installed globally, see [`PYTHON_CLEANUP_GUIDE.md`](./PYTHON_CLEANUP_GUIDE.md) for detailed cleanup instructions.

### Environment Verification

Always verify your environment before running security scans:

```bash
# Check if virtual environment is active
echo $VIRTUAL_ENV  # Linux/Mac (should show path to venv)
echo %VIRTUAL_ENV%  # Windows (should show path to venv)

# Verify Python location
which python  # Linux/Mac (should point to venv/bin/python)
where python  # Windows (should point to venv\Scripts\python.exe)

# List installed packages (should only show project dependencies)
pip list
```

### Security Best Practices Summary

- ✅ **ALWAYS** use virtual environments for development
- ✅ **NEVER** install packages globally unless absolutely necessary
- ✅ Use Docker containers for production deployments
- ✅ Verify your environment before running security tools
- ✅ Clean up any global packages using the cleanup guide
- ✅ The configuration files in this project don't automatically install anything