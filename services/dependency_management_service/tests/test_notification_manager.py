"""Tests for notification system."""

import json
import os
from datetime import datetime
from unittest import mock

import pytest
import requests

from ..notifications.notification_manager import (NotificationChannel,
                                               NotificationConfig,
                                               NotificationManager)

@pytest.fixture
def config_file():
    """Create a temporary config file"""
    config = {
        "notification_channels": {
            "slack": {
                "enabled": True,
                "channels": {
                    "tier1": "critical-deps",
                    "tier2": "important-deps"
                }
            },
            "teams": {
                "enabled": True,
                "channels": {
                    "tier1": "Critical Dependencies",
                    "tier2": "Important Dependencies"
                }
            },
            "email": {
                "enabled": True,
                "lists": {
                    "tier1": ["core@company.com"],
                    "tier2": ["dev@company.com"]
                }
            }
        }
    }
    
    with open("test_notification_config.json", "w") as f:
        json.dump(config, f)
    return "test_notification_config.json"

@pytest.fixture
def notification_manager(config_file):
    """Create a notification manager instance"""
    return NotificationManager(config_file, "notifications/templates")

def test_load_config(notification_manager):
    """Test loading configuration"""
    assert notification_manager.config.slack.enabled
    assert notification_manager.config.teams.enabled
    assert notification_manager.config.email.enabled
    assert "tier1" in notification_manager.config.slack.config["channels"]

def test_get_notification_level(notification_manager):
    """Test notification level determination"""
    assert notification_manager._get_notification_level("vulnerability", "tier1") == "critical"
    assert notification_manager._get_notification_level("breaking_change", "tier1") == "high"
    assert notification_manager._get_notification_level("error", "tier2") == "normal"

def test_should_notify(notification_manager):
    """Test notification deduplication"""
    assert notification_manager._should_notify("test:vuln", "critical")
    assert not notification_manager._should_notify("test:vuln", "critical")

@mock.patch('requests.post')
def test_send_slack_notification(mock_post, notification_manager):
    """Test Slack notification"""
    mock_post.return_value.status_code = 200
    os.environ["SLACK_WEBHOOK_URL"] = "http://test-slack"
    
    assert notification_manager.send_slack_notification(
        "test-channel",
        "Test message",
        "critical"
    )
    mock_post.assert_called_once()

@mock.patch('requests.post')
def test_send_teams_notification(mock_post, notification_manager):
    """Test Teams notification"""
    mock_post.return_value.status_code = 200
    os.environ["TEAMS_WEBHOOK_URL"] = "http://test-teams"
    
    assert notification_manager.send_teams_notification(
        "test-channel",
        "Test message",
        "high"
    )
    mock_post.assert_called_once()

@mock.patch('smtplib.SMTP')
def test_send_email_notification(mock_smtp, notification_manager):
    """Test email notification"""
    mock_smtp.return_value.__enter__.return_value.send_message.return_value = {}
    os.environ.update({
        "SMTP_HOST": "test-smtp",
        "SMTP_PORT": "587",
        "SMTP_USER": "test@company.com",
        "SMTP_PASS": "test-pass"
    })
    
    assert notification_manager.send_email_notification(
        ["test@company.com"],
        "Test Subject",
        "Test message",
        "critical"
    )

def test_format_notification(notification_manager):
    """Test notification formatting"""
    issue = {
        "dependency": "TestRepo",
        "tier": "tier1",
        "type": "vulnerability",
        "details": {
            "severity": "CRITICAL",
            "description": "Test vulnerability"
        }
    }
    
    # Test Slack format
    slack_msg = notification_manager.format_notification(
        issue,
        "slack_notification.j2"
    )
    assert "TestRepo" in slack_msg
    assert "CRITICAL" in slack_msg
    
    # Test Teams format
    teams_msg = notification_manager.format_notification(
        issue,
        "teams_notification.j2"
    )
    assert "TestRepo" in teams_msg
    assert "CRITICAL" in teams_msg

@mock.patch.object(NotificationManager, 'send_slack_notification')
@mock.patch.object(NotificationManager, 'send_teams_notification')
@mock.patch.object(NotificationManager, 'send_email_notification')
def test_notify_issue(
    mock_email,
    mock_teams,
    mock_slack,
    notification_manager
):
    """Test full issue notification"""
    mock_slack.return_value = True
    mock_teams.return_value = True
    mock_email.return_value = True
    
    issue = {
        "dependency": "TestRepo",
        "tier": "tier1",
        "type": "vulnerability",
        "details": {
            "severity": "CRITICAL",
            "description": "Test vulnerability"
        }
    }
    
    assert notification_manager.notify_issue(issue)
    mock_slack.assert_called_once()
    mock_teams.assert_called_once()
    mock_email.assert_called_once()

@mock.patch.object(NotificationManager, 'send_slack_notification')
@mock.patch.object(NotificationManager, 'send_teams_notification')
@mock.patch.object(NotificationManager, 'send_email_notification')
def test_notify_weekly_summary(
    mock_email,
    mock_teams,
    mock_slack,
    notification_manager
):
    """Test weekly summary notification"""
    mock_slack.return_value = True
    mock_teams.return_value = True
    mock_email.return_value = True
    
    from ..monitoring.dependency_monitor import DependencyStatus, VulnerabilityInfo
    
    status_updates = [
        DependencyStatus(
            name="TestRepo",
            tier="tier1",
            last_check=datetime.utcnow(),
            last_update=datetime.utcnow(),
            current_commit="test-sha",
            vulnerabilities=[
                VulnerabilityInfo(
                    id="test-vuln",
                    severity="CRITICAL",
                    description="Test vulnerability",
                    affected_versions=["1.0.0"],
                    fix_versions=["1.0.1"],
                    cve_ids=["CVE-2025-1234"],
                    discovered_date="2025-08-24T00:00:00Z"
                )
            ]
        )
    ]
    
    assert notification_manager.notify_weekly_summary(status_updates)
    mock_slack.assert_called()
    mock_teams.assert_called()
    mock_email.assert_called()
