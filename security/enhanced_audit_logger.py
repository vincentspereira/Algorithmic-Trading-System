#!/usr/bin/env python3
"""
Enhanced Audit Logger
Advanced security logging and audit trail system
"""

import logging
import json
import csv
import uuid
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import asdict
from pathlib import Path
import sqlite3

from authentication_framework import AuthenticationManager, AuditEvent, AuditEventType

logger = logging.getLogger(__name__)

class AuditLoggerConfig:
    """Configuration for audit logger"""
    
    def __init__(self):
        self.log_to_file = True
        self.log_file_path = "security_audit.log"
        self.log_format = "json"  # json or text
        self.enable_database_storage = True
        self.database_path = "security_audit.db"
        self.retention_days = 2555  # 7 years
        self.log_levels = {
            AuditEventType.LOGIN_SUCCESS: logging.INFO,
            AuditEventType.LOGIN_FAILURE: logging.WARNING,
            AuditEventType.LOGOUT: logging.INFO,
            AuditEventType.PASSWORD_CHANGE: logging.INFO,
            AuditEventType.MFA_SETUP: logging.INFO,
            AuditEventType.MFA_DISABLE: logging.INFO,
            AuditEventType.PERMISSION_GRANTED: logging.INFO,
            AuditEventType.PERMISSION_DENIED: logging.WARNING,
            AuditEventType.SESSION_EXPIRED: logging.INFO,
            AuditEventType.ACCOUNT_LOCKED: logging.ERROR,
            AuditEventType.ACCOUNT_UNLOCKED: logging.INFO,
            AuditEventType.SENSITIVE_DATA_ACCESS: logging.WARNING,
            AuditEventType.SYSTEM_CONFIG_CHANGE: logging.WARNING
        }

class EnhancedAuditLogger:
    """Enhanced security audit logging system"""
    
    def __init__(self, auth_manager: AuthenticationManager, 
                 config: Optional[AuditLoggerConfig] = None):
        self.auth_manager = auth_manager
        self.config = config or AuditLoggerConfig()
        # Keep track of file handlers for proper cleanup
        self.file_handlers = []
        self._setup_logging()
        self._setup_database()
    
    def _setup_logging(self):
        """Set up file logging"""
        if not self.config.log_to_file:
            return
        
        # Create log file handler
        log_file = Path(self.config.log_file_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(self.config.log_file_path)
        self.file_handlers.append(file_handler)
        
        # Set formatter based on format
        if self.config.log_format == "json":
            formatter = logging.Formatter('%(message)s')
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.setLevel(logging.INFO)
    
    def _setup_database(self):
        """Set up database for audit events"""
        if not self.config.enable_database_storage:
            return
        
        db_path = Path(self.config.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(self.config.database_path, check_same_thread=False)
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE,
                event_type TEXT,
                user_id TEXT,
                username TEXT,
                session_id TEXT,
                timestamp TEXT,
                ip_address TEXT,
                user_agent TEXT,
                resource TEXT,
                action TEXT,
                result TEXT,
                details TEXT,
                risk_score INTEGER
            )
        ''')
        self.conn.commit()
    
    def close(self):
        """Close file handlers and database connection"""
        # Remove file handlers
        for handler in self.file_handlers:
            logger.removeHandler(handler)
            handler.close()
        self.file_handlers.clear()
        
        # Close database connection
        if hasattr(self, 'conn'):
            self.conn.close()
    
    def log_event(self, event: AuditEvent):
        """Log audit event to all configured destinations"""
        # Log to file
        if self.config.log_to_file:
            self._log_to_file(event)
        
        # Log to database
        if self.config.enable_database_storage:
            self._log_to_database(event)
        
        # Log to system logger
        self._log_to_system_logger(event)
    
    def _log_to_file(self, event: AuditEvent):
        """Log event to file"""
        try:
            event_dict = event.to_dict()
            
            if self.config.log_format == "json":
                # JSON format
                log_message = json.dumps(event_dict, separators=(',', ':'))
                logger.info(log_message)
            else:
                # Text format
                log_message = (
                    f"Event: {event_dict['event_type']} | "
                    f"User: {event_dict['username']} | "
                    f"IP: {event_dict['ip_address']} | "
                    f"Result: {event_dict['result']} | "
                    f"Risk: {event_dict['risk_score']}"
                )
                logger.info(log_message)
        except Exception as e:
            logger.error(f"Failed to log event to file: {e}")
    
    def _log_to_database(self, event: AuditEvent):
        """Log event to database"""
        try:
            event_dict = event.to_dict()
            
            # Convert details to JSON string for storage
            details_json = json.dumps(event_dict['details'])
            
            self.conn.execute('''
                INSERT OR IGNORE INTO audit_events (
                    event_id, event_type, user_id, username, session_id,
                    timestamp, ip_address, user_agent, resource, action,
                    result, details, risk_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event_dict['event_id'],
                event_dict['event_type'],
                event_dict['user_id'],
                event_dict['username'],
                event_dict['session_id'],
                event_dict['timestamp'],
                event_dict['ip_address'],
                event_dict['user_agent'],
                event_dict['resource'],
                event_dict['action'],
                event_dict['result'],
                details_json,
                event_dict['risk_score']
            ))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to log event to database: {e}")
    
    def _log_to_system_logger(self, event: AuditEvent):
        """Log event to system logger"""
        try:
            # Determine log level based on event type and result
            log_level = self.config.log_levels.get(event.event_type, logging.INFO)
            if event.result == "FAILURE":
                log_level = logging.WARNING
            elif event.result == "ERROR":
                log_level = logging.ERROR
            
            # Create log message
            log_message = (
                f"Security Event: {event.event_type.value} - "
                f"{event.result} - User: {event.username} - "
                f"IP: {event.ip_address} - Risk: {event.risk_score}"
            )
            
            logger.log(log_level, log_message)
        except Exception as e:
            logger.error(f"Failed to log event to system logger: {e}")
    
    def query_events(self, 
                    event_types: Optional[List[AuditEventType]] = None,
                    user_ids: Optional[List[str]] = None,
                    usernames: Optional[List[str]] = None,
                    ip_addresses: Optional[List[str]] = None,
                    start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None,
                    min_risk_score: Optional[int] = None,
                    max_risk_score: Optional[int] = None,
                    limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Query audit events with various filters
        
        Returns:
            List of event dictionaries
        """
        if not self.config.enable_database_storage:
            return []
        
        try:
            # Build query
            query = "SELECT * FROM audit_events WHERE 1=1"
            params = []
            
            # Add filters
            if event_types:
                event_type_values = [et.value for et in event_types]
                placeholders = ','.join(['?' for _ in event_type_values])
                query += f" AND event_type IN ({placeholders})"
                params.extend(event_type_values)
            
            if user_ids:
                placeholders = ','.join(['?' for _ in user_ids])
                query += f" AND user_id IN ({placeholders})"
                params.extend(user_ids)
            
            if usernames:
                placeholders = ','.join(['?' for _ in usernames])
                query += f" AND username IN ({placeholders})"
                params.extend(usernames)
            
            if ip_addresses:
                placeholders = ','.join(['?' for _ in ip_addresses])
                query += f" AND ip_address IN ({placeholders})"
                params.extend(ip_addresses)
            
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())
            
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())
            
            if min_risk_score is not None:
                query += " AND risk_score >= ?"
                params.append(min_risk_score)
            
            if max_risk_score is not None:
                query += " AND risk_score <= ?"
                params.append(max_risk_score)
            
            query += " ORDER BY timestamp DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            # Execute query
            cursor = self.conn.execute(query, params)
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            events = []
            for row in rows:
                event_dict = dict(zip(columns, row))
                # Parse details JSON
                try:
                    event_dict['details'] = json.loads(event_dict['details'])
                except:
                    event_dict['details'] = {}
                events.append(event_dict)
            
            return events
        except Exception as e:
            logger.error(f"Failed to query audit events: {e}")
            return []
    
    def export_events(self, 
                     file_path: str,
                     format: str = "csv",
                     event_types: Optional[List[AuditEventType]] = None,
                     start_time: Optional[datetime] = None,
                     end_time: Optional[datetime] = None) -> bool:
        """
        Export audit events to file
        
        Args:
            file_path: Path to export file
            format: Export format (csv, json)
            event_types: Filter by event types
            start_time: Filter by start time
            end_time: Filter by end time
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Query events
            events = self.query_events(
                event_types=event_types,
                start_time=start_time,
                end_time=end_time
            )
            
            if format.lower() == "csv":
                return self._export_to_csv(file_path, events)
            elif format.lower() == "json":
                return self._export_to_json(file_path, events)
            else:
                logger.error(f"Unsupported export format: {format}")
                return False
        except Exception as e:
            logger.error(f"Failed to export audit events: {e}")
            return False
    
    def _export_to_csv(self, file_path: str, events: List[Dict[str, Any]]) -> bool:
        """Export events to CSV file"""
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                if not events:
                    # Write empty file with headers
                    fieldnames = [
                        'event_id', 'event_type', 'user_id', 'username', 'session_id',
                        'timestamp', 'ip_address', 'user_agent', 'resource', 'action',
                        'result', 'details', 'risk_score'
                    ]
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    return True
                
                # Write events
                writer = csv.DictWriter(csvfile, fieldnames=events[0].keys())
                writer.writeheader()
                for event in events:
                    writer.writerow(event)
            
            return True
        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}")
            return False
    
    def _export_to_json(self, file_path: str, events: List[Dict[str, Any]]) -> bool:
        """Export events to JSON file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(events, jsonfile, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}")
            return False
    
    def get_audit_summary(self, 
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get audit event summary statistics
        
        Returns:
            Dictionary with summary statistics
        """
        if not self.config.enable_database_storage:
            return {}
        
        try:
            # Set default time range (last 24 hours)
            if not end_time:
                end_time = datetime.now()
            if not start_time:
                start_time = end_time - timedelta(hours=24)
            
            # Query summary data
            cursor = self.conn.execute('''
                SELECT 
                    COUNT(*) as total_events,
                    COUNT(CASE WHEN result = 'SUCCESS' THEN 1 END) as successful_events,
                    COUNT(CASE WHEN result = 'FAILURE' THEN 1 END) as failed_events,
                    COUNT(CASE WHEN risk_score >= 50 THEN 1 END) as high_risk_events,
                    AVG(risk_score) as average_risk_score
                FROM audit_events 
                WHERE timestamp >= ? AND timestamp <= ?
            ''', (start_time.isoformat(), end_time.isoformat()))
            
            summary = cursor.fetchone()
            
            # Get event type counts
            cursor = self.conn.execute('''
                SELECT event_type, COUNT(*) as count
                FROM audit_events 
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY event_type
                ORDER BY count DESC
            ''', (start_time.isoformat(), end_time.isoformat()))
            
            event_type_counts = dict(cursor.fetchall())
            
            return {
                'period_start': start_time.isoformat(),
                'period_end': end_time.isoformat(),
                'total_events': summary[0] if summary[0] else 0,
                'successful_events': summary[1] if summary[1] else 0,
                'failed_events': summary[2] if summary[2] else 0,
                'high_risk_events': summary[3] if summary[3] else 0,
                'average_risk_score': round(summary[4], 2) if summary[4] else 0,
                'event_type_counts': event_type_counts
            }
        except Exception as e:
            logger.error(f"Failed to get audit summary: {e}")
            return {}
    
    def cleanup_old_events(self):
        """Clean up old audit events based on retention policy"""
        if not self.config.enable_database_storage:
            return
        
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config.retention_days)
            
            # Clean up database
            self.conn.execute(
                "DELETE FROM audit_events WHERE timestamp < ?",
                (cutoff_date.isoformat(),)
            )
            self.conn.commit()
            
            logger.info(f"Cleaned up audit events older than {cutoff_date}")
        except Exception as e:
            logger.error(f"Failed to clean up old audit events: {e}")

# Integration with AuthenticationManager
def integrate_audit_logger(auth_manager: AuthenticationManager, 
                          config: Optional[AuditLoggerConfig] = None) -> EnhancedAuditLogger:
    """
    Integrate enhanced audit logger with authentication manager
    
    This function enhances the existing audit logging by:
    1. Adding file and database storage
    2. Providing query and export capabilities
    3. Adding summary statistics
    """
    audit_logger = EnhancedAuditLogger(auth_manager, config)
    
    # Store reference to the enhanced audit logger
    auth_manager._enhanced_audit_logger = audit_logger
    
    # Override the _log_audit_event method to use enhanced logging
    original_log_method = auth_manager._log_audit_event
    
    def enhanced_log_audit_event(event_type: AuditEventType, user_id: Optional[str] = None,
                               username: Optional[str] = None, session_id: Optional[str] = None,
                               ip_address: str = "unknown", user_agent: str = "unknown",
                               resource: Optional[str] = None, action: Optional[str] = None,
                               result: str = "SUCCESS", details: Optional[Dict[str, Any]] = None,
                               risk_score: int = 0):
        # Call original method first (this will create and store the event in memory)
        original_log_method(
            event_type, user_id, username, session_id, ip_address, user_agent,
            resource, action, result, details, risk_score
        )
        
        # Get the last event that was added to the audit_events list
        # This is the event that was just created by the original method
        if auth_manager.audit_events:
            event = auth_manager.audit_events[-1]
            # Log to enhanced audit logger
            audit_logger.log_event(event)
    
    # Replace the method
    auth_manager._log_audit_event = enhanced_log_audit_event
    
    return audit_logger

# Example usage
if __name__ == "__main__":
    print("Enhanced Audit Logger module loaded")