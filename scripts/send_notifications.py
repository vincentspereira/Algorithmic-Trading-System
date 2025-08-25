#!/usr/bin/env python3

import argparse
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime

def send_email_notification(email_addr, version_data, activity_data):
    """Send notification email with monitoring results"""
    
    # Load all status results
    results = {}
    for status_type, filename in status_files.items():
        try:
            with open(filename) as f:
                results[status_type] = json.load(f)
        except Exception as e:
            print(f"Error loading {status_type} results: {e}")
            results[status_type] = {'error': str(e)}

    # Create email content
    msg = MIMEMultipart()
    msg['Subject'] = 'Dependency Monitoring Alert'
    msg['From'] = os.getenv('SMTP_FROM', 'noreply@trading-system.com')
    msg['To'] = email_addr

    # Generate HTML report
    html = """
    <html>
      <head>
        <style>
          .red { color: red; }
          .yellow { color: #ffa500; }
          .green { color: green; }
        </style>
      </head>
      <body>
        <h2>Dependency Monitoring Report</h2>
    """

    for status_type, data in results.items():
        html += f"<h3>{status_type.replace('_', ' ').title()}</h3>"
        html += "<ul>"
        for item in data:
            status_class = item.get('status', 'red')
            html += f'<li class="{status_class}">{item["name"]}: {item.get("error", "OK")}</li>'
        html += "</ul>"

    html += """
      </body>
    </html>
    """

    msg.attach(MIMEText(html, 'html'))

    # Send email
    try:
        with smtplib.SMTP(os.getenv('SMTP_HOST', 'localhost')) as server:
            if os.getenv('SMTP_USER') and os.getenv('SMTP_PASS'):
                server.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASS'))
            server.send_message(msg)
    except Exception as e:
        print(f"Error sending email: {e}")
        raise

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--email', required=True)
    parser.add_argument('--version-status', required=True)
    parser.add_argument('--security-status', required=True)
    parser.add_argument('--activity-status', required=True)
    parser.add_argument('--drift-status', required=True)
    args = parser.parse_args()
    
    status_files = {
        'version': args.version_status,
        'security': args.security_status,
        'activity': args.activity_status,
        'drift': args.drift_status
    }
    
    send_email_notification(args.email, status_files)
