# Dependency Monitoring System Documentation

## Overview
The dependency monitoring system automatically tracks version updates and activity for critical dependencies in the Algorithmic Trading System. It uses a tiered approach to prioritize monitoring frequency and provides automated notifications for important updates.

## Features
- Automated version checking
- Repository activity monitoring
- Tiered dependency management
- Email notifications with status reports
- GitHub Actions integration
- Scheduled monitoring (6-hourly for Tier 1, daily for Tier 2)

## Adding New Dependencies

### 1. Update dependencies.json
Add your dependency to the appropriate tier in `dependency_management/dependencies.json`:

```json
{
  "tier1": {
    "dependencies": [
      {
        "name": "DependencyName",
        "repository": "https://github.com/owner/repo",
        "version": "1.0.0",
        "repo_path": "./dependencies/dep_name",
        "customizations": ["List of customizations"],
        "integration_points": ["List of integration points"],
        "monitoring_frequency": "daily",
        "alert_channels": ["slack", "email", "teams"],
        "ccb_required": true
      }
    ]
  }
}
```

### 2. Required Fields
- `name`: Display name of the dependency
- `repository`: GitHub repository URL
- `version`: Current version in use
- `repo_path`: Local path or reference path

### 3. Optional Fields
- `customizations`: List of custom modifications
- `integration_points`: Where the dependency is used
- `monitoring_frequency`: How often to check
- `alert_channels`: Where to send alerts
- `ccb_required`: Whether CCB approval is needed for updates

## Monitoring Configuration

### Version Checking
The system checks for:
- Major version updates (triggers red alert)
- Minor version updates (triggers yellow alert)
- Patch updates (informational)

### Activity Monitoring
Tracks:
- Last commit date
- Months since last activity
- Repository status

### Alert Thresholds
- Red: Major version difference or >12 months inactivity
- Yellow: Minor version difference or >6 months inactivity
- Green: Up to date and active

## Troubleshooting Guide

### Common Issues

1. Email Notifications Not Received
- Check SMTP credentials in GitHub secrets
- Verify email address is correct
- Check spam folder
- Review GitHub Actions logs

2. Version Check Failures
- Verify GitHub token permissions
- Check repository URL format
- Ensure version format is consistent

3. Activity Monitoring Issues
- Confirm repository accessibility
- Check API rate limits
- Verify GitHub token scope

4. Workflow Failures
- Check Python dependencies
- Verify file paths
- Review GitHub Actions logs

## Backup and Recovery

### Configuration Backup
The system maintains backups of:
- dependencies.json
- Monitoring configurations
- GitHub Actions workflows

### Backup Location
- Primary: `backups/` directory
- Timestamp-based backup files
- JSON format for easy restoration

### Recovery Procedure
1. Identify the latest valid backup
2. Replace corrupted configuration
3. Validate dependencies.json format
4. Test monitoring workflow
5. Verify notifications

### Emergency Contacts
- System Administrator: TBD
- DevOps Team: TBD
- Security Team: TBD

## Security Considerations
- GitHub tokens stored as secrets
- SMTP credentials protected
- Access controls on configuration files
- Rate limiting on API calls
- Audit logging enabled
