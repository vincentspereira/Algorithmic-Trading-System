#!/usr/bin/env python3
"""
Tests for Enhanced Audit Logger Implementation
"""

import unittest
import sys
import os
import json
import csv
from datetime import datetime, timedelta
from pathlib import Path

# Add the security directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from authentication_framework import AuthenticationManager, UserRole, AuditEventType
from enhanced_audit_logger import EnhancedAuditLogger, AuditLoggerConfig, integrate_audit_logger


class TestEnhancedAuditLogger(unittest.TestCase):
    """Test cases for Enhanced Audit Logger Implementation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.auth_manager = AuthenticationManager()
        self.config = AuditLoggerConfig()
        self.config.log_file_path = "test_security_audit.log"
        self.config.database_path = "test_security_audit.db"
        # Use integration function to properly set up audit logging
        self.audit_logger = integrate_audit_logger(self.auth_manager, self.config)
        
        # Create test user
        self.test_user = self.auth_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="SecureTest123!",
            roles={UserRole.TRADER}
        )
    
    def tearDown(self):
        """Clean up test files"""
        # Close the audit logger to release file handles
        if hasattr(self, 'audit_logger'):
            self.audit_logger.close()
        
        # Remove test log file
        log_file = Path(self.config.log_file_path)
        if log_file.exists():
            try:
                log_file.unlink()
            except Exception as e:
                print(f"Warning: Could not delete log file: {e}")
        
        # Remove test database
        db_file = Path(self.config.database_path)
        if db_file.exists():
            try:
                db_file.unlink()
            except Exception as e:
                print(f"Warning: Could not delete database file: {e}")
    
    def test_log_event_to_file(self):
        """Test logging event to file"""
        # Trigger some events
        session = self.auth_manager.authenticate_user(
            username="testuser",
            password="SecureTest123!",
            ip_address="192.168.1.100"
        )
        
        self.assertIsNotNone(session)
        
        # Close the audit logger to flush file contents
        self.audit_logger.close()
        
        # Check if log file was created
        log_file = Path(self.config.log_file_path)
        self.assertTrue(log_file.exists())
        
        # Check if log file has content
        content = log_file.read_text()
        self.assertIn("LOGIN_SUCCESS", content)
        self.assertIn("testuser", content)
    
    def test_log_event_to_database(self):
        """Test logging event to database"""
        # Trigger some events
        session = self.auth_manager.authenticate_user(
            username="testuser",
            password="SecureTest123!",
            ip_address="192.168.1.100"
        )
        
        self.assertIsNotNone(session)
        
        # Close the audit logger to flush database contents
        self.audit_logger.close()
        
        # Create a new audit logger instance to access the database
        # (since we closed the previous one)
        new_audit_logger = EnhancedAuditLogger(self.auth_manager, self.config)
        
        # Query events from database
        events = new_audit_logger.query_events()
        self.assertGreater(len(events), 0)
        
        # Check if login success event is in the results
        login_events = [e for e in events if e['event_type'] == 'LOGIN_SUCCESS']
        self.assertGreater(len(login_events), 0)
        self.assertEqual(login_events[0]['username'], 'testuser')
        self.assertEqual(login_events[0]['ip_address'], '192.168.1.100')
        
        # Close the new audit logger
        new_audit_logger.close()
    
    def test_query_events_with_filters(self):
        """Test querying events with filters"""
        # Trigger some events
        session = self.auth_manager.authenticate_user(
            username="testuser",
            password="SecureTest123!",
            ip_address="192.168.1.100"
        )
        
        self.assertIsNotNone(session)
        
        # Close the audit logger to flush database contents
        self.audit_logger.close()
        
        # Create a new audit logger instance to access the database
        new_audit_logger = EnhancedAuditLogger(self.auth_manager, self.config)
        
        # Query with event type filter
        events = new_audit_logger.query_events(
            event_types=[AuditEventType.LOGIN_SUCCESS]
        )
        self.assertGreater(len(events), 0)
        for event in events:
            self.assertEqual(event['event_type'], 'LOGIN_SUCCESS')
        
        # Query with user filter
        events = new_audit_logger.query_events(
            usernames=['testuser']
        )
        self.assertGreater(len(events), 0)
        for event in events:
            self.assertEqual(event['username'], 'testuser')
        
        # Query with IP filter
        events = new_audit_logger.query_events(
            ip_addresses=['192.168.1.100']
        )
        self.assertGreater(len(events), 0)
        for event in events:
            self.assertEqual(event['ip_address'], '192.168.1.100')
        
        # Close the new audit logger
        new_audit_logger.close()
    
    def test_export_events_csv(self):
        """Test exporting events to CSV"""
        # Trigger some events
        session = self.auth_manager.authenticate_user(
            username="testuser",
            password="SecureTest123!",
            ip_address="192.168.1.100"
        )
        
        self.assertIsNotNone(session)
        
        # Close the audit logger to flush database contents
        self.audit_logger.close()
        
        # Create a new audit logger instance to access the database
        new_audit_logger = EnhancedAuditLogger(self.auth_manager, self.config)
        
        # Export to CSV
        export_file = "test_export.csv"
        success = new_audit_logger.export_events(export_file, "csv")
        self.assertTrue(success)
        
        # Check if export file exists
        export_path = Path(export_file)
        self.assertTrue(export_path.exists())
        
        # Check CSV content
        with open(export_file, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            self.assertGreater(len(rows), 0)
        
        # Clean up
        if export_path.exists():
            export_path.unlink()
        
        # Close the new audit logger
        new_audit_logger.close()
    
    def test_export_events_json(self):
        """Test exporting events to JSON"""
        # Trigger some events
        session = self.auth_manager.authenticate_user(
            username="testuser",
            password="SecureTest123!",
            ip_address="192.168.1.100"
        )
        
        self.assertIsNotNone(session)
        
        # Close the audit logger to flush database contents
        self.audit_logger.close()
        
        # Create a new audit logger instance to access the database
        new_audit_logger = EnhancedAuditLogger(self.auth_manager, self.config)
        
        # Export to JSON
        export_file = "test_export.json"
        success = new_audit_logger.export_events(export_file, "json")
        self.assertTrue(success)
        
        # Check if export file exists
        export_path = Path(export_file)
        self.assertTrue(export_path.exists())
        
        # Check JSON content
        with open(export_file, 'r') as jsonfile:
            data = json.load(jsonfile)
            self.assertIsInstance(data, list)
            self.assertGreater(len(data), 0)
        
        # Clean up
        if export_path.exists():
            export_path.unlink()
        
        # Close the new audit logger
        new_audit_logger.close()
    
    def test_get_audit_summary(self):
        """Test getting audit summary"""
        # Trigger some events
        session = self.auth_manager.authenticate_user(
            username="testuser",
            password="SecureTest123!",
            ip_address="192.168.1.100"
        )
        
        self.assertIsNotNone(session)
        
        # Close the audit logger to flush database contents
        self.audit_logger.close()
        
        # Create a new audit logger instance to access the database
        new_audit_logger = EnhancedAuditLogger(self.auth_manager, self.config)
        
        # Get audit summary
        summary = new_audit_logger.get_audit_summary()
        
        self.assertIsInstance(summary, dict)
        self.assertIn('total_events', summary)
        self.assertIn('successful_events', summary)
        self.assertIn('failed_events', summary)
        self.assertIn('high_risk_events', summary)
        self.assertIn('average_risk_score', summary)
        self.assertIn('event_type_counts', summary)
        
        # Check that we have at least one successful event
        self.assertGreater(summary['successful_events'], 0)
        
        # Close the new audit logger
        new_audit_logger.close()
    
    def test_cleanup_old_events(self):
        """Test cleaning up old events"""
        # Trigger some events
        session = self.auth_manager.authenticate_user(
            username="testuser",
            password="SecureTest123!",
            ip_address="192.168.1.100"
        )
        
        self.assertIsNotNone(session)
        
        # Close the audit logger to flush database contents
        self.audit_logger.close()
        
        # Create a new audit logger instance to access the database
        new_audit_logger = EnhancedAuditLogger(self.auth_manager, self.config)
        
        # Check initial event count
        initial_events = new_audit_logger.query_events()
        initial_count = len(initial_events)
        
        # Clean up old events (this won't actually delete anything since they're not old enough)
        new_audit_logger.cleanup_old_events()
        
        # Check event count after cleanup
        events_after_cleanup = new_audit_logger.query_events()
        count_after_cleanup = len(events_after_cleanup)
        
        # Should be the same since events are not old enough
        self.assertEqual(initial_count, count_after_cleanup)
        
        # Close the new audit logger
        new_audit_logger.close()
    
    def test_integrate_audit_logger(self):
        """Test integrating enhanced audit logger with authentication manager"""
        # Create new auth manager and config for integration test
        auth_manager = AuthenticationManager()
        config = AuditLoggerConfig()
        config.log_file_path = "integration_test_security_audit.log"
        config.database_path = "integration_test_security_audit.db"
        
        # Integrate audit logger
        audit_logger = integrate_audit_logger(auth_manager, config)
        
        # Create test user
        test_user = auth_manager.create_user(
            username="integration_test_user",
            email="integration_test@example.com",
            password="SecureTest123!",
            roles={UserRole.TRADER}
        )
        
        # Trigger an event
        session = auth_manager.authenticate_user(
            username="integration_test_user",
            password="SecureTest123!",
            ip_address="192.168.1.101"
        )
        
        self.assertIsNotNone(session)
        
        # Close the audit logger to flush contents
        audit_logger.close()
        
        # Create a new audit logger instance to access the database
        new_audit_logger = EnhancedAuditLogger(auth_manager, config)
        
        # Check if event was logged to enhanced logger
        events = new_audit_logger.query_events()
        self.assertGreater(len(events), 0)
        
        # Close the new audit logger
        new_audit_logger.close()
        
        # Clean up integration test files
        log_file = Path(config.log_file_path)
        if log_file.exists():
            try:
                log_file.unlink()
            except Exception as e:
                print(f"Warning: Could not delete log file: {e}")
        
        db_file = Path(config.database_path)
        if db_file.exists():
            try:
                db_file.unlink()
            except Exception as e:
                print(f"Warning: Could not delete database file: {e}")


def run_tests():
    """Run all enhanced audit logger tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestEnhancedAuditLogger))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)