#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def send_email(to_email, subject, html_content):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = os.getenv('SMTP_USER')
    msg['To'] = to_email
    
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        with smtplib.SMTP(os.getenv('SMTP_HOST', 'smtp.gmail.com'), 587) as server:
            server.starttls()
            server.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASS'))
            server.send_message(msg)
            print(f"Alert sent to {to_email}")
            return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def generate_html_report(version_data, activity_data):
    html = f"""
    <html>
        <head>
            <style>
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ padding: 8px; text-align: left; border: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
                .red {{ background-color: #ffcccc; }}
                .yellow {{ background-color: #ffffcc; }}
                .green {{ background-color: #ccffcc; }}
            </style>
        </head>
        <body>
            <h2>Dependency Monitor Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}</h2>
            
            <h3>Version Status</h3>
            <table>
                <tr>
                    <th>Dependency</th>
                    <th>Current Version</th>
                    <th>Latest Version</th>
                    <th>Status</th>
                </tr>
    """
    
    for dep in version_data:
        status = dep.get('status', 'red')
        if 'error' in dep:
            html += f"""
                <tr class="{status}">
                    <td>{dep['name']}</td>
                    <td colspan="3">Error: {dep['error']}</td>
                </tr>
            """
        else:
            html += f"""
                <tr class="{status}">
                    <td>{dep['name']}</td>
                    <td>{dep['current_version']}</td>
                    <td>{dep['latest_version']}</td>
                    <td>{status.upper()}</td>
                </tr>
            """
    
    html += """
            </table>
            
            <h3>Activity Status</h3>
            <table>
                <tr>
                    <th>Dependency</th>
                    <th>Last Commit</th>
                    <th>Months Since Activity</th>
                    <th>Status</th>
                </tr>
    """
    
    for dep in activity_data:
        status = dep.get('status', 'red')
        if 'error' in dep:
            html += f"""
                <tr class="{status}">
                    <td>{dep['name']}</td>
                    <td colspan="3">Error: {dep['error']}</td>
                </tr>
            """
        else:
            html += f"""
                <tr class="{status}">
                    <td>{dep['name']}</td>
                    <td>{dep['last_commit']}</td>
                    <td>{dep['months_since']:.1f}</td>
                    <td>{status.upper()}</td>
                </tr>
            """
    
    html += """
            </table>
        </body>
    </html>
    """
    return html

def main():
    parser = argparse.ArgumentParser(description='Send dependency monitoring alerts')
    parser.add_argument('--email', required=True, help='Email address to send alerts to')
    parser.add_argument('--version-status', required=True, help='Path to version status JSON file')
    parser.add_argument('--activity-status', required=True, help='Path to activity status JSON file')
    
    args = parser.parse_args()
    
    try:
        with open(args.version_status) as f:
            version_data = json.load(f)
    except Exception as e:
        print(f"Error loading version status: {e}")
        version_data = []
        
    try:
        with open(args.activity_status) as f:
            activity_data = json.load(f)
    except Exception as e:
        print(f"Error loading activity status: {e}")
        activity_data = []
    
    html_content = generate_html_report(version_data, activity_data)
    send_email(
        args.email,
        f"Dependency Monitor Alert - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        html_content
    )

if __name__ == '__main__':
    main()
