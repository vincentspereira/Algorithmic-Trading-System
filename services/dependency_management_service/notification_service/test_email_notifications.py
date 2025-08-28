#!/usr/bin/env python3
\"\"\"
Email Notification Test Script
Tests the enhanced email notification functionality.
\"\"\"

import asyncio
import os
import sys
from datetime import datetime

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from notification_service import (
    NotificationService,
    NotificationPayload,
    EmailNotificationService,
    send_dependency_update_email
)

async def test_email_notifications():
    \"\"\"Test email notification functionality\"\"\"
    print(\"🧪 Testing Email Notification System...\")
    
    # Initialize services
    notification_service = NotificationService()
    email_service = EmailNotificationService(notification_service)
    
    # Check if email configuration is available
    if not notification_service.config.email_config:
        print(\"❌ Email configuration not found in environment variables.\")
        print(\"Please ensure EMAIL_HOST_USER and EMAIL_HOST_PASSWORD are set.\")
        return False
    
    print(f\"✅ Email configuration loaded:\")
    print(f\"   SMTP Server: {notification_service.config.email_config['smtp_server']}\")
    print(f\"   SMTP Port: {notification_service.config.email_config['smtp_port']}\")
    print(f\"   Sender: {notification_service.config.email_config['sender']}\")
    print(f\"   TLS Enabled: {notification_service.config.email_config['use_tls']}\")
    
    try:
        # Test 1: Critical Security Alert
        print(\"\n📧 Test 1: Sending critical security alert...\")
        await email_service.send_security_alert_email(
            dependency_name=\"nautilus_trader\",
            cve_details={
                \"cve_id\": \"CVE-2024-TEST-001\",
                \"severity\": \"CRITICAL\",
                \"cvss_score\": \"9.8\",
                \"description\": \"Remote code execution vulnerability in trading engine\",
                \"remediation\": \"Update to version 1.191.0 immediately\"
            }
        )
        print(\"✅ Critical security alert sent successfully\")
        
        # Test 2: Dependency Update Notification
        print(\"\n📧 Test 2: Sending dependency update notification...\")
        await send_dependency_update_email(
            email_service=email_service,
            dependency_name=\"fastapi\",
            old_version=\"0.104.0\",
            new_version=\"0.105.0\",
            tier=2,
            breaking_changes=False
        )
        print(\"✅ Dependency update notification sent successfully\")
        
        # Test 3: General Notification
        print(\"\n📧 Test 3: Sending general notification...\")
        test_payload = NotificationPayload(
            title=\"🔧 System Maintenance Notification\",
            message=\"Scheduled maintenance window for dependency management system\",
            priority=\"medium\",
            tier=3,
            timestamp=datetime.utcnow(),
            details={
                \"maintenance_type\": \"scheduled\",
                \"duration\": \"2 hours\",
                \"affected_services\": [\"dependency-monitor\", \"notification-service\"],
                \"start_time\": \"2024-12-10 02:00 UTC\",
                \"end_time\": \"2024-12-10 04:00 UTC\"
            },
            recipients=[\"vincyspereira@gmail.com\"]
        )
        
        await email_service.send_immediate_email([\"vincyspereira@gmail.com\"], test_payload)
        print(\"✅ General notification sent successfully\")
        
        # Test 4: Batch Summary (simulated)
        print(\"\n📧 Test 4: Sending batch summary...\")
        
        # Add some notifications to batch
        email_service.add_to_batch({
            \"dependency\": \"kafka\",
            \"tier\": 1,
            \"priority\": \"medium\",
            \"message\": \"Minor version update available\"
        })
        
        email_service.add_to_batch({
            \"dependency\": \"redis\",
            \"tier\": 4,
            \"priority\": \"low\",
            \"message\": \"Patch update available\"
        })
        
        await email_service.send_batch_summary_email(\"daily\")
        print(\"✅ Batch summary sent successfully\")
        
        print(\"\n🎉 All email notification tests completed successfully!\")
        return True
        
    except Exception as e:
        print(f\"\n❌ Email notification test failed: {e}\")
        import traceback
        traceback.print_exc()
        return False

def check_environment_setup():
    \"\"\"Check if all required environment variables are set\"\"\"
    print(\"🔍 Checking environment setup...\")
    
    required_vars = [
        \"EMAIL_HOST\",
        \"EMAIL_PORT\", 
        \"EMAIL_HOST_USER\",
        \"EMAIL_HOST_PASSWORD\"
    ]
    
    optional_vars = [
        \"TEAMS_WEBHOOK_URL\",
        \"SLACK_WEBHOOK_URL\",
        \"DISCORD_WEBHOOK_URL\",
        \"EMAIL_USE_TLS\",
        \"EMAIL_USE_SSL\"
    ]
    
    missing_required = []
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
        else:
            print(f\"✅ {var}: {'*' * len(os.getenv(var, ''))[:8]}...\")
    
    if missing_required:
        print(f\"\n❌ Missing required environment variables: {missing_required}\")
        print(\"Please ensure these are set in your .env file.\")
        return False
    
    print(\"\n📋 Optional environment variables:\")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            display_value = \"*\" * min(len(value), 20) if value else \"Not set\"
            print(f\"✅ {var}: {display_value}\")
        else:
            print(f\"⚠️  {var}: Not set\")
    
    print(\"\n✅ Environment setup check completed\")
    return True

async def main():
    \"\"\"Main test function\"\"\"
    print(\"🚀 Email Notification System Test\")
    print(\"=\" * 50)
    
    # Check environment setup
    if not check_environment_setup():
        print(\"\n❌ Environment setup check failed. Please fix the issues above.\")
        return
    
    # Test email notifications
    success = await test_email_notifications()
    
    if success:
        print(\"\n🎉 All tests passed! Email notification system is working correctly.\")
        print(\"\n📧 Check your email inbox for the test notifications.\")
    else:
        print(\"\n❌ Some tests failed. Please check the configuration and try again.\")

if __name__ == \"__main__\":
    # Load environment variables from .env file if python-dotenv is available
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print(\"✅ Loaded environment variables from .env file\")
    except ImportError:
        print(\"⚠️  python-dotenv not available, using system environment variables\")
    
    asyncio.run(main())