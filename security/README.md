# Security Scanning Implementation

This directory contains the comprehensive security scanning implementation for the Algorithmic Trading System.

## Overview

The security scanning system provides multi-layered security analysis including:

1. **Static Application Security Testing (SAST)** using Bandit
2. **Dependency Vulnerability Scanning** using Safety and pip-audit
3. **Threat Modeling** using STRIDE methodology
4. **Container Security Scanning** using Trivy
5. **Secrets Detection** using Semgrep

## Components

### 1. Comprehensive Security Scan Script
- `comprehensive_security_scan.py` - Main orchestration script
- Runs all security tools and generates consolidated reports
- Integrates Bandit, Safety, pip-audit, and custom threat modeling

### 2. Threat Modeling
- `threat_modeling.py` - Automated STRIDE threat modeling
- Analyzes system components for potential security threats
- Generates detailed threat model reports

### 3. Security Reports
- All security scan results are stored in the `security_reports/` directory
- JSON and text format reports for each tool
- Summary reports for quick overview

### 4. GitHub Actions Workflows
- `.github/workflows/comprehensive-security-scan.yml` - Main security scanning workflow
- `.github/workflows/enhanced-security-scanning.yml` - Additional security scanning workflow

## Tools Used

### Bandit
Static analysis tool designed to find common security issues in Python code.

### Safety
Checks installed dependencies against known vulnerabilities in the PyUp safety database.

### pip-audit
Audits Python environments and dependencies for known vulnerabilities.

### Semgrep
Fast, open-source, static analysis engine for finding bugs, detecting vulnerabilities, and enforcing code standards.

### Trivy
Comprehensive security scanner for containers and other artifacts.

## Running Security Scans

### Local Execution
```bash
# Run comprehensive security scan
python security/comprehensive_security_scan.py

# Run threat modeling
python security/threat_modeling.py
```

### Docker Execution
```bash
# Build security scanner image
docker build -t security-scanner -f security/Dockerfile .

# Run security scanner
docker run --rm security-scanner
```

## Configuration

### Environment Variables
- `NVD_API_KEY` - API key for NVD vulnerability database
- `SEMGREP_APP_TOKEN` - Token for Semgrep cloud platform
- `TEAMS_WEBHOOK_URL` - Webhook URL for Microsoft Teams notifications

### Bandit Configuration
- `dependency_management/security/bandit_config.yaml` - Custom Bandit rules and configuration

## Reports

Security scan reports are generated in the following formats:
- JSON (for machine parsing)
- Text (for human reading)
- SARIF (for integration with code scanning tools)

## Integration with CI/CD

The security scanning is integrated into the GitHub Actions CI/CD pipeline:
- Runs on every push and pull request to main/develop branches
- Scheduled daily scans for continuous monitoring
- Manual triggering via workflow dispatch

## Threat Modeling

The STRIDE threat modeling implementation analyzes system components for:
- **Spoofing** - Impersonation of legitimate users or systems
- **Tampering** - Unauthorized modification of data or code
- **Repudiation** - Denial of actions or transactions
- **Information Disclosure** - Unauthorized access to sensitive data
- **Denial of Service** - Making systems unavailable
- **Elevation of Privilege** - Unauthorized access to higher privilege levels

## Security Dashboard

Security metrics and reports are integrated with the monitoring dashboard:
- Real-time security issue tracking
- Vulnerability trend analysis
- Compliance reporting

## Testing

Security scanning implementation can be tested with:
```bash
python security/test_security_scanning.py
```

## Requirements

See `requirements.txt` for the list of Python dependencies required for security scanning.