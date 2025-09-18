#!/usr/bin/env python3
"""
Critical alerts notification system for dependency management.
Sends immediate notifications for critical dependency issues.
"""

import json
import os
import sys
import requests
from datetime import datetime, timezone
from pathlib import Path

def send_teams_notification(webhook_url, message):
    """Send notification to Microsoft Teams."""
    if not webhook_url:
        print("Teams webhook URL not configured")
        return False
        
    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "FF0000",  # Red for critical alerts
        "summary": "Critical Dependency Alert",
        "sections": [{
            "activityTitle": "🚨 Critical Dependency Alert",
            "activitySubtitle": f"Algorithmic Trading System - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "activityImage": "https://cdn-icons-png.flaticon.com/512/1828/1828665.png",
            "facts": [{
                "name": "Alert Type",
                "value": "Critical Dependency Issue"
            }, {
                "name": "Timestamp",
                "value": datetime.now(timezone.utc).isoformat()
            }, {
                "name": "Repository",
                "value": os.environ.get('GITHUB_REPOSITORY', 'Unknown')
            }],
            "markdown": True,
            "text": message
        }]
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=30)
        response.raise_for_status()
        print("Teams notification sent successfully")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Failed to send Teams notification: {e}")
        return False

def send_discord_notification(webhook_url, message):
    """Send notification to Discord."""
    if not webhook_url:
        print("Discord webhook URL not configured")
        return False
        
    payload = {
        "embeds": [{
            "title": "🚨 Critical Dependency Alert",
            "description": message,
            "color": 0xFF0000,  # Red color
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {
                "text": "Algorithmic Trading System Dependency Monitor"
            },
            "fields": [{
                "name": "Repository",
                "value": os.environ.get('GITHUB_REPOSITORY', 'Unknown'),
                "inline": True
            }, {
                "name": "Workflow",
                "value": os.environ.get('GITHUB_WORKFLOW', 'Unknown'),
                "inline": True
            }]
        }]
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=30)
        response.raise_for_status()
        print("Discord notification sent successfully")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Failed to send Discord notification: {e}")
        return False

def create_github_issue(title, body, labels):
    """Create a GitHub issue for the critical alert."""
    github_token = os.environ.get('GITHUB_TOKEN')
    github_repo = os.environ.get('GITHUB_REPOSITORY')
    
    if not github_token or not github_repo:
        print("GitHub token or repository not configured")
        return False
        
    url = f"https://api.github.com/repos/{github_repo}/issues"
    headers = {
        'Authorization': f'Bearer {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    payload = {
        'title': title,
        'body': body,
        'labels': labels
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        issue_data = response.json()
        print(f"GitHub issue created: #{issue_data['number']}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Failed to create GitHub issue: {e}")
        return False

def format_critical_message():
    """Format the critical alert message based on current context."""
    workflow_name = os.environ.get('GITHUB_WORKFLOW', 'Unknown Workflow')
    job_name = os.environ.get('GITHUB_JOB', 'Unknown Job')
    run_id = os.environ.get('GITHUB_RUN_ID', 'Unknown')
    
    message = f"""
## 🚨 Critical Dependency Alert

**Workflow Failed:** {workflow_name}
**Job:** {job_name}
**Run ID:** {run_id}

### Issue Details:
- **Severity:** CRITICAL
- **Component:** Tier 1 Dependencies
- **Impact:** Potential system instability or security vulnerability

### Immediate Actions Required:
1. 🔍 **Review Failed Workflow:** Check the workflow logs for specific failures
2. 🛡️ **Security Assessment:** Verify if security vulnerabilities are present
3. ⚡ **Priority Response:** Address critical dependencies within 2 hours
4. 📋 **Escalation:** Notify team leads and stakeholders immediately

### Workflow Details:
- **Repository:** {os.environ.get('GITHUB_REPOSITORY', 'Unknown')}
- **Branch:** {os.environ.get('GITHUB_REF_NAME', 'Unknown')}
- **Commit:** {os.environ.get('GITHUB_SHA', 'Unknown')[:8]}
- **Actor:** {os.environ.get('GITHUB_ACTOR', 'Unknown')}

### Next Steps:
1. Review the [workflow run](https://github.com/{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/{run_id})
2. Check dependency monitoring dashboard
3. Apply necessary patches or rollbacks
4. Update team on resolution status

**This is an automated alert from the Dependency Management System.**
"""
    return message.strip()

def main():
    """Main function to send critical alerts."""
    print("Sending critical dependency alerts...")
    
    # Get webhook URLs from environment
    teams_webhook = os.environ.get('TEAMS_WEBHOOK')
    discord_webhook = os.environ.get('DISCORD_WEBHOOK')
    
    # Format the critical message
    message = format_critical_message()
    
    # Send notifications
    teams_success = send_teams_notification(teams_webhook, message)
    discord_success = send_discord_notification(discord_webhook, message)
    
    # Create GitHub issue for tracking
    issue_title = f"🚨 Critical Dependency Alert - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    issue_labels = ['critical', 'dependencies', 'security', 'tier1']
    
    github_success = create_github_issue(issue_title, message, issue_labels)
    
    # Report results
    success_count = sum([teams_success, discord_success, github_success])
    total_channels = 3
    
    print(f"Alert sent to {success_count}/{total_channels} channels")
    
    if success_count == 0:
        print("❌ Failed to send alerts to any channel!")
        sys.exit(1)
    elif success_count < total_channels:
        print("⚠️ Some alert channels failed")
        sys.exit(1)
    else:
        print("✅ All alerts sent successfully")
        sys.exit(0)

if __name__ == "__main__":
    main()