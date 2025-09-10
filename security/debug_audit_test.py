#!/usr/bin/env python3
"""
Debug test for Enhanced Audit Logger
"""

import os
import sys
from pathlib import Path

# Add the security directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from authentication_framework import AuthenticationManager, UserRole, AuditEventType
from enhanced_audit_logger import EnhancedAuditLogger, AuditLoggerConfig, integrate_audit_logger

def test_audit_logger():
    print("Testing Enhanced Audit Logger...")
    
    # Create auth manager
    auth_manager = AuthenticationManager()
    config = AuditLoggerConfig()
    config.log_file_path = "debug_test_audit.log"
    config.database_path = "debug_test_audit.db"
    
    # Integrate audit logger with auth manager
    audit_logger = integrate_audit_logger(auth_manager, config)
    
    # Create test user
    print("Creating test user...")
    test_user = auth_manager.create_user(
        username="debug_test_user",
        email="debug_test@example.com",
        password="SecureTest123!",
        roles={UserRole.TRADER}
    )
    print("User created successfully")
    
    # Authenticate user
    print("Authenticating user...")
    session = auth_manager.authenticate_user(
        username="debug_test_user",
        password="SecureTest123!",
        ip_address="192.168.1.102"
    )
    
    if session:
        print("User authenticated successfully")
        
        # Close the audit logger to flush contents
        print("Closing audit logger...")
        audit_logger.close()
        
        # Check if log file was created
        log_file = Path(config.log_file_path)
        if log_file.exists():
            print("Log file created successfully")
            content = log_file.read_text()
            print(f"Log file content:\n{content}")
        else:
            print("Log file not created")
        
        # Check if database was created
        db_file = Path(config.database_path)
        if db_file.exists():
            print("Database file created successfully")
            
            # Create a new audit logger to query the database
            new_audit_logger = EnhancedAuditLogger(auth_manager, config)
            
            # Query events
            events = new_audit_logger.query_events()
            print(f"Found {len(events)} audit events in database")
            for event in events:
                print(f"Event: {event['event_type']} - {event['username']}")
            
            # Close the new audit logger
            new_audit_logger.close()
        else:
            print("Database file not created")
        
        # Clean up test files
        if log_file.exists():
            try:
                log_file.unlink()
                print("Log file cleaned up")
            except Exception as e:
                print(f"Could not delete log file: {e}")
        
        if db_file.exists():
            try:
                db_file.unlink()
                print("Database file cleaned up")
            except Exception as e:
                print(f"Could not delete database file: {e}")
    else:
        print("User authentication failed")
        
    print("Test completed")

if __name__ == "__main__":
    test_audit_logger()