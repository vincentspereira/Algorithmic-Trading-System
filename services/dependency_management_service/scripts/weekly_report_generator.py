#!/usr/bin/env python3
"""
Weekly dependency report generator.
Consolidates all dependency updates and generates comprehensive reports.
"""

import json
import os
import sys
import requests
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

class WeeklyReportGenerator:
    """Generates comprehensive weekly dependency reports."""
    
    def __init__(self):
        self.github_token = os.environ.get('GITHUB_TOKEN')
        self.github_repo = os.environ.get('GITHUB_REPOSITORY')
        self.teams_webhook = os.environ.get('TEAMS_WEBHOOK')
        self.base_path = Path(__file__).parent.parent
        
    def load_dependencies(self):
        """Load all dependency configurations."""
        deps_file = self.base_path / 'dependencies.json'
        if not deps_file.exists():
            raise FileNotFoundError(f"Dependencies file not found: {deps_file}")
            
        with open(deps_file, 'r') as f:
            return json.load(f)
    
    def get_recent_updates(self, days=7):
        """Get dependency updates from the last N days."""
        # This would typically query your dependency monitoring logs
        # For now, we'll simulate with placeholder data
        
        updates = {
            'tier1': [
                {
                    'name': 'nautilus_trader',
                    'old_version': '1.190.0',
                    'new_version': '1.191.0',
                    'update_type': 'minor',
                    'security_impact': 'none',
                    'breaking_changes': False,
                    'changelog_url': 'https://github.com/nautechsystems/nautilus_trader/releases/tag/1.191.0'
                }
            ],
            'tier2': [
                {
                    'name': 'transformers',
                    'old_version': '4.36.0',
                    'new_version': '4.37.0',
                    'update_type': 'minor',
                    'security_impact': 'low',
                    'breaking_changes': False,
                    'changelog_url': 'https://github.com/huggingface/transformers/releases/tag/v4.37.0'
                }
            ],
            'tier3': [],
            'tier4': []
        }
        
        return updates
    
    def get_security_alerts(self, days=7):
        """Get security alerts from the last N days."""
        # This would query your security monitoring system
        alerts = [
            {
                'severity': 'medium',
                'package': 'requests',
                'vulnerability': 'CVE-2023-XXXX',
                'description': 'Potential security issue in requests library',
                'affected_versions': '<2.31.0',
                'fixed_version': '2.31.0',
                'recommended_action': 'Update to latest version'
            }
        ]
        
        return alerts
    
    def get_failed_updates(self, days=7):
        """Get failed update attempts from the last N days."""
        # This would query your CI/CD logs
        failed_updates = [
            {
                'dependency': 'some-package',
                'tier': 'tier2',
                'reason': 'Breaking API changes',
                'last_attempt': '2024-01-15T10:30:00Z',
                'next_retry': '2024-01-22T10:30:00Z'
            }
        ]
        
        return failed_updates
    
    def generate_html_report(self, updates, security_alerts, failed_updates):
        """Generate HTML report for email/web viewing."""
        report_date = datetime.now().strftime('%Y-%m-%d')
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Weekly Dependency Report - {report_date}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #2E86AB; color: white; padding: 20px; text-align: center; }}
        .section {{ margin: 20px 0; padding: 15px; border-left: 4px solid #2E86AB; }}
        .tier {{ margin: 10px 0; padding: 10px; background-color: #f5f5f5; }}
        .alert-high {{ border-left-color: #dc3545; }}
        .alert-medium {{ border-left-color: #ffc107; }}
        .alert-low {{ border-left-color: #28a745; }}
        .success {{ color: #28a745; }}
        .warning {{ color: #ffc107; }}
        .danger {{ color: #dc3545; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Weekly Dependency Report</h1>
        <p>Algorithmic Trading System - Week ending {report_date}</p>
    </div>
    
    <div class="section">
        <h2>📈 Summary</h2>
        <p><strong>Total Updates Available:</strong> {sum(len(updates[tier]) for tier in updates)}</p>
        <p><strong>Security Alerts:</strong> {len(security_alerts)}</p>
        <p><strong>Failed Updates:</strong> {len(failed_updates)}</p>
    </div>
"""
        
        # Add updates by tier
        for tier, tier_updates in updates.items():
            if tier_updates:
                html += f"""
    <div class="section">
        <h2>🔧 {tier.title()} Updates</h2>
        <table>
            <tr>
                <th>Package</th>
                <th>Old Version</th>
                <th>New Version</th>
                <th>Type</th>
                <th>Breaking Changes</th>
                <th>Security Impact</th>
            </tr>
"""
                for update in tier_updates:
                    breaking_icon = "⚠️" if update['breaking_changes'] else "✅"
                    security_class = "danger" if update['security_impact'] != 'none' else "success"
                    
                    html += f"""
            <tr>
                <td><a href="{update['changelog_url']}">{update['name']}</a></td>
                <td>{update['old_version']}</td>
                <td>{update['new_version']}</td>
                <td>{update['update_type']}</td>
                <td>{breaking_icon}</td>
                <td class="{security_class}">{update['security_impact']}</td>
            </tr>
"""
                html += """
        </table>
    </div>
"""
        
        # Add security alerts
        if security_alerts:
            html += """
    <div class="section alert-high">
        <h2>🚨 Security Alerts</h2>
        <table>
            <tr>
                <th>Package</th>
                <th>Severity</th>
                <th>Vulnerability</th>
                <th>Affected Versions</th>
                <th>Fixed Version</th>
                <th>Action Required</th>
            </tr>
"""
            for alert in security_alerts:
                severity_class = f"alert-{alert['severity']}"
                html += f"""
            <tr class="{severity_class}">
                <td>{alert['package']}</td>
                <td>{alert['severity'].upper()}</td>
                <td>{alert['vulnerability']}</td>
                <td>{alert['affected_versions']}</td>
                <td>{alert['fixed_version']}</td>
                <td>{alert['recommended_action']}</td>
            </tr>
"""
            html += """
        </table>
    </div>
"""
        
        html += """
    <div class="section">
        <h2>📋 Next Week's Actions</h2>
        <ul>
            <li>Review and approve pending updates</li>
            <li>Monitor security alerts and apply patches</li>
            <li>Test critical dependency updates in staging</li>
            <li>Update dependency documentation</li>
        </ul>
    </div>
    
    <div class="section">
        <h2>🔗 Resources</h2>
        <ul>
            <li><a href="#">Dependency Dashboard</a></li>
            <li><a href="#">Security Monitoring</a></li>
            <li><a href="#">Update Guidelines</a></li>
            <li><a href="#">Emergency Procedures</a></li>
        </ul>
    </div>
</body>
</html>
"""
        return html
    
    def send_teams_report(self, html_report, summary):
        """Send report to Microsoft Teams."""
        if not self.teams_webhook:
            print("Teams webhook not configured")
            return False
            
        # Create a condensed version for Teams
        message = f"""
## 📊 Weekly Dependency Report

**Report Date:** {datetime.now().strftime('%Y-%m-%d')}

### Summary:
- **Total Updates:** {summary['total_updates']}
- **Security Alerts:** {summary['security_alerts']}
- **Failed Updates:** {summary['failed_updates']}

### Key Actions Required:
{chr(10).join(f"- {action}" for action in summary['actions'])}

### Critical Items:
{chr(10).join(f"- ⚠️ {item}" for item in summary['critical_items'])}

[View Full Report]({summary.get('report_url', '#')})
"""
        
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "0078D4",
            "summary": "Weekly Dependency Report",
            "sections": [{
                "activityTitle": "📊 Weekly Dependency Report",
                "activitySubtitle": f"Algorithmic Trading System - {datetime.now().strftime('%Y-%m-%d')}",
                "markdown": True,
                "text": message
            }]
        }
        
        try:
            response = requests.post(self.teams_webhook, json=payload, timeout=30)
            response.raise_for_status()
            print("Teams report sent successfully")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Failed to send Teams report: {e}")
            return False
    
    def save_report_file(self, html_report):
        """Save report to file system."""
        report_date = datetime.now().strftime('%Y-%m-%d')
        reports_dir = self.base_path / 'reports'
        reports_dir.mkdir(exist_ok=True)
        
        report_file = reports_dir / f'weekly-report-{report_date}.html'
        
        with open(report_file, 'w') as f:
            f.write(html_report)
            
        print(f"Report saved to: {report_file}")
        return report_file
    
    def generate_report(self):
        """Generate the complete weekly report."""
        print("Generating weekly dependency report...")
        
        try:
            # Gather data
            dependencies = self.load_dependencies()
            updates = self.get_recent_updates()
            security_alerts = self.get_security_alerts()
            failed_updates = self.get_failed_updates()
            
            # Generate HTML report
            html_report = self.generate_html_report(updates, security_alerts, failed_updates)
            
            # Save report file
            report_file = self.save_report_file(html_report)
            
            # Create summary for notifications
            summary = {
                'total_updates': sum(len(updates[tier]) for tier in updates),
                'security_alerts': len(security_alerts),
                'failed_updates': len(failed_updates),
                'actions': [
                    "Review Tier 1 updates for immediate application",
                    "Address security alerts within 48 hours",
                    "Retry failed updates with manual intervention"
                ],
                'critical_items': [
                    item['description'] for item in security_alerts 
                    if item['severity'] in ['high', 'critical']
                ],
                'report_url': f"file://{report_file}"
            }
            
            # Send notifications
            teams_success = self.send_teams_report(html_report, summary)
            
            print("✅ Weekly report generation completed")
            return True
            
        except Exception as e:
            print(f"❌ Failed to generate weekly report: {e}")
            return False

def main():
    """Main function."""
    generator = WeeklyReportGenerator()
    success = generator.generate_report()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()