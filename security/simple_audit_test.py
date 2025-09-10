#!/usr/bin/env python3
"""
Simple test for Enhanced Audit Logger
"""

import os
import sys
from pathlib import Path

# Add the security directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from authentication_framework import AuthenticationManager, UserRole
    from enhanced_audit_logger import EnhancedAuditLogger, AuditLoggerConfig
    
    print("Modules imported successfully")
    
    # Create auth manager and audit logger
    auth_manager = AuthenticationManager()
    config = AuditLoggerConfig()
    config.log_file_path = "simple_test_audit.log"
    config.database_path = "simple_test_audit.db"
    
    audit_logger = EnhancedAuditLogger(auth_manager, config)
    
    # Create test user
    test_user = auth_manager.create_user(
        username="simple_test_user",
        email="simple_test@example.com",
        password="SecureTest123!",
        roles={UserRole.TRADER}
    )
    
    print("User created successfully")
    
    # Authenticate user
    session = auth_manager.authenticate_user(
        username="simple_test_user",
        password="SecureTest123!",
        ip_address="192.168.1.102"
    )
    
    if session:
        print("User authenticated successfully")
        
        # Close the audit logger to flush contents
        audit_logger.close()
        
        # Check if log file was created
        log_file = Path(config.log_file_path)
        if log_file.exists():
            print("Log file created successfully")
            content = log_file.read_text()
            if "LOGIN_SUCCESS" in content:
                print("Login event logged to file")
            else:
                print("Login event not found in log file")
                print(f"Log file content: {content}")
        else:
            print("Log file not created")
        
        # Check if database was created
        db_file = Path(config.database_path)
        if db_file.exists():
            print("Database file created successfully")
            
            # Query events
            events = audit_logger.query_events()
            if events:
                print(f"Found {len(events)} audit events in database")
                login_events = [e for e in events if e['event_type'] == 'LOGIN_SUCCESS']
                if login_events:
                    print("Login event found in database")
                else:
                    print("Login event not found in database")
            else:
                print("No events found in database")
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
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()