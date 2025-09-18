#!/usr/bin/env python3
"""
Tier 1 Critical Notification System
Sends immediate alerts for critical repository issues
"""

import json
import os
import sys
import argparse
import requests
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any

class Tier1NotificationService:
    def __init__(self, summary_file: str):
        self.summary_file = summary_file
        self.summary = self._load_summary()
        
        # Notification endpoints
        self.teams_webhook = os.getenv('TEAMS_WEBHOOK')
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK')
        self.email_recipients = os.getenv('EMAIL_RECIPIENTS', '').split(',')
        
        # SMTP configuration
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
    
    def _load_summary(self) -> Dict[str, Any]:
        """Load monitoring summary from JSON file"""
        try:
            with open(self.summary_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading summary: {e}")
            return {}
    
    def should_send_notification(self) -> bool:
        """Determine if notification should be sent for Tier 1 (always alert)"""
        if not self.summary:
            return False
        
        overall = self.summary.get('overall', {})
        return (
            overall.get('status') in ['critical', 'warning'] or
            overall.get('critical_issues', 0) > 0 or
            overall.get('total_issues', 0) > 0
        )
    
    def generate_teams_message(self) -> Dict[str, Any]:
        """Generate Microsoft Teams adaptive card message"""
        overall = self.summary.get('overall', {})
        metadata = self.summary.get('metadata', {})
        
        # Determine color based on status
        color_map = {
            'critical': 'attention',  # Red
            'warning': 'warning',     # Yellow
            'healthy': 'good'         # Green
        }
        
        status = overall.get('status', 'unknown')
        color = color_map.get(status, 'default')
        
        # Build facts for the card
        facts = [
            {'name': 'Repository', 'value': metadata.get('repository', 'Unknown')},
            {'name': 'Tier', 'value': f"Tier {metadata.get('tier')} ({metadata.get('tier_name')})"}, 
            {'name': 'Status', 'value': status.upper()},
            {'name': 'Total Issues', 'value': str(overall.get('total_issues', 0))},
            {'name': 'Critical Issues', 'value': str(overall.get('critical_issues', 0))},
            {'name': 'Run ID', 'value': metadata.get('run_id', 'Unknown')}
        ]
        
        # Add component details
        components = self.summary.get('components', {})
        component_text = []
        for comp_name, comp_data in components.items():
            issues = len(comp_data.get('issues', []))
            comp_status = comp_data.get('status', 'unknown')
            component_text.append(f"• **{comp_name.title()}**: {comp_status} ({issues} issues)")
        
        # Build recommendations
        recommendations = self.summary.get('recommendations', [])
        rec_text = '\n'.join(f"• {rec}" for rec in recommendations[:5])  # Limit to 5
        
        card = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": f"Tier 1 Critical Alert: {status.upper()}",
            "themeColor": "FF0000" if status == 'critical' else "FFA500" if status == 'warning' else "00FF00",
            "sections": [
                {
                    "activityTitle": "🚨 Tier 1 Critical Repository Alert",
                    "activitySubtitle": f"Status: {status.upper()}",
                    "facts": facts,
                    "text": f"**Component Status:**\n{''.join(component_text) if component_text else 'No components reported'}"
                },
                {
                    "activityTitle": "📋 Immediate Actions Required",
                    "text": rec_text if rec_text else "No specific recommendations available"
                }
            ],
            "potentialAction": [
                {
                    "@type": "OpenUri",
                    "name": "View GitHub Actions",
                    "targets": [
                        {
                            "os": "default",
                            "uri": f"https://github.com/{metadata.get('repository', '')}/actions/runs/{metadata.get('run_id', '')}"
                        }
                    ]
                }
            ]
        }
        
        return card
    
    def generate_discord_message(self) -> Dict[str, Any]:
        """Generate Discord webhook message"""
        overall = self.summary.get('overall', {})
        metadata = self.summary.get('metadata', {})
        
        # Determine embed color
        color_map = {
            'critical': 0xFF0000,  # Red
            'warning': 0xFFA500,   # Orange
            'healthy': 0x00FF00    # Green
        }
        
        status = overall.get('status', 'unknown')
        color = color_map.get(status, 0x808080)
        
        # Build embed fields
        fields = [
            {'name': 'Repository', 'value': metadata.get('repository', 'Unknown'), 'inline': True},
            {'name': 'Tier', 'value': f"Tier {metadata.get('tier')} ({metadata.get('tier_name')})", 'inline': True},
            {'name': 'Status', 'value': status.upper(), 'inline': True},
            {'name': 'Total Issues', 'value': str(overall.get('total_issues', 0)), 'inline': True},
            {'name': 'Critical Issues', 'value': str(overall.get('critical_issues', 0)), 'inline': True},
            {'name': 'Run ID', 'value': metadata.get('run_id', 'Unknown'), 'inline': True}
        ]
        
        # Add component summary
        components = self.summary.get('components', {})
        if components:
            comp_summary = []
            for comp_name, comp_data in components.items():
                issues = len(comp_data.get('issues', []))
                comp_status = comp_data.get('status', 'unknown')
                emoji = '🔴' if comp_status == 'failed' else '🟡' if comp_status == 'warning' else '🟢'
                comp_summary.append(f"{emoji} **{comp_name.title()}**: {issues} issues")
            
            fields.append({
                'name': 'Component Status',
                'value': '\n'.join(comp_summary[:10]),  # Limit to 10 components
                'inline': False
            })
        
        # Add recommendations
        recommendations = self.summary.get('recommendations', [])
        if recommendations:
            fields.append({
                'name': 'Immediate Actions',
                'value': '\n'.join(f"• {rec}" for rec in recommendations[:5]),
                'inline': False
            })
        
        embed = {
            'title': '🚨 Tier 1 Critical Repository Alert',
            'description': f'Critical monitoring alert for {metadata.get("repository", "Unknown Repository")}',
            'color': color,
            'fields': fields,
            'timestamp': datetime.utcnow().isoformat(),
            'footer': {
                'text': f'Algorithmic Trading System - Tier 1 Monitoring'
            }
        }
        
        return {'embeds': [embed]}
    
    def generate_email_content(self) -> tuple[str, str]:
        """Generate email subject and HTML content"""
        overall = self.summary.get('overall', {})
        metadata = self.summary.get('metadata', {})
        
        status = overall.get('status', 'unknown')
        repository = metadata.get('repository', 'Unknown')
        
        subject = f"🚨 CRITICAL ALERT: Tier 1 Repository Issues - {repository} ({status.upper()})"
        
        # Generate HTML content
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: {'#ff4444' if status == 'critical' else '#ffaa44' if status == 'warning' else '#44ff44'}; 
                          color: white; padding: 15px; border-radius: 5px; }}
                .section {{ margin: 20px 0; padding: 15px; border-left: 4px solid #ccc; }}
                .critical {{ border-left-color: #ff4444; }}
                .warning {{ border-left-color: #ffaa44; }}
                .info {{ border-left-color: #4444ff; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; 
                          background-color: #f5f5f5; border-radius: 3px; }}
                ul {{ margin: 10px 0; }}
                li {{ margin: 5px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚨 Tier 1 Critical Repository Alert</h1>
                <p>Repository: {repository}</p>
                <p>Status: {status.upper()}</p>
                <p>Timestamp: {metadata.get('timestamp', 'Unknown')}</p>
            </div>
            
            <div class="section critical">
                <h2>📊 Summary Metrics</h2>
                <div class="metric">
                    <strong>Total Issues:</strong> {overall.get('total_issues', 0)}
                </div>
                <div class="metric">
                    <strong>Critical Issues:</strong> {overall.get('critical_issues', 0)}
                </div>
                <div class="metric">
                    <strong>Alert Threshold:</strong> {overall.get('alert_threshold', 0)}
                </div>
                <div class="metric">
                    <strong>Run ID:</strong> {metadata.get('run_id', 'Unknown')}
                </div>
            </div>
        """
        
        # Add component details
        components = self.summary.get('components', {})
        if components:
            html_content += '<div class="section info"><h2>🔍 Component Details</h2><ul>'
            for comp_name, comp_data in components.items():
                issues = len(comp_data.get('issues', []))
                comp_status = comp_data.get('status', 'unknown')
                html_content += f'<li><strong>{comp_name.title()}:</strong> {comp_status} ({issues} issues)</li>'
            html_content += '</ul></div>'
        
        # Add recommendations
        recommendations = self.summary.get('recommendations', [])
        if recommendations:
            html_content += '<div class="section warning"><h2>📋 Immediate Actions Required</h2><ul>'
            for rec in recommendations:
                html_content += f'<li>{rec}</li>'
            html_content += '</ul></div>'
        
        # Add footer
        github_url = f"https://github.com/{repository}/actions/runs/{metadata.get('run_id', '')}"
        html_content += f"""
            <div class="section info">
                <h2>🔗 Links</h2>
                <p><a href="{github_url}">View GitHub Actions Run</a></p>
                <p><a href="https://github.com/{repository}">Repository</a></p>
            </div>
            
            <div class="section">
                <p><em>This is an automated alert from the Algorithmic Trading System Tier 1 monitoring.</em></p>
                <p><em>Please address critical issues immediately to maintain system stability.</em></p>
            </div>
        </body>
        </html>
        """
        
        return subject, html_content
    
    def send_teams_notification(self) -> bool:
        """Send notification to Microsoft Teams"""
        if not self.teams_webhook:
            print("Teams webhook not configured")
            return False
        
        try:
            message = self.generate_teams_message()
            response = requests.post(self.teams_webhook, json=message, timeout=30)
            response.raise_for_status()
            print("✅ Teams notification sent successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to send Teams notification: {e}")
            return False
    
    def send_discord_notification(self) -> bool:
        """Send notification to Discord"""
        if not self.discord_webhook:
            print("Discord webhook not configured")
            return False
        
        try:
            message = self.generate_discord_message()
            response = requests.post(self.discord_webhook, json=message, timeout=30)
            response.raise_for_status()
            print("✅ Discord notification sent successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to send Discord notification: {e}")
            return False
    
    def send_email_notifications(self) -> bool:
        """Send email notifications"""
        if not self.email_recipients or not self.smtp_username or not self.smtp_password:
            print("Email configuration incomplete")
            return False
        
        try:
            subject, html_content = self.generate_email_content()
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_username
            msg['To'] = ', '.join(self.email_recipients)
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            print(f"✅ Email notifications sent to {len(self.email_recipients)} recipients")
            return True
        except Exception as e:
            print(f"❌ Failed to send email notifications: {e}")
            return False
    
    def send_all_notifications(self) -> None:
        """Send notifications via all configured channels"""
        if not self.should_send_notification():
            print("ℹ️  No notification needed - all checks passed")
            return
        
        print("🚨 Sending Tier 1 critical notifications...")
        
        results = {
            'teams': self.send_teams_notification(),
            'discord': self.send_discord_notification(), 
            'email': self.send_email_notifications()
        }
        
        success_count = sum(results.values())
        total_channels = len([k for k, v in {
            'teams': self.teams_webhook,
            'discord': self.discord_webhook,
            'email': self.email_recipients and self.smtp_username
        }.items() if v])
        
        print(f"📊 Notification Summary: {success_count}/{total_channels} channels successful")
        
        if success_count == 0:
            print("⚠️  All notification channels failed!")
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Send Tier 1 critical notifications')
    parser.add_argument('--summary', required=True, help='Path to monitoring summary JSON file')
    
    args = parser.parse_args()
    
    service = Tier1NotificationService(args.summary)
    service.send_all_notifications()

if __name__ == '__main__':
    main()