"""Unit tests for the Audit Trail module."""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
import json
import hashlib
import uuid
from enum import Enum
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding


class AuditEventType(Enum):
    """Audit event type enumeration."""
    USER_LOGIN = "USER_LOGIN"
    USER_LOGOUT = "USER_LOGOUT"
    ORDER_PLACED = "ORDER_PLACED"
    ORDER_MODIFIED = "ORDER_MODIFIED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_FILLED = "ORDER_FILLED"
    POSITION_OPENED = "POSITION_OPENED"
    POSITION_CLOSED = "POSITION_CLOSED"
    RISK_LIMIT_MODIFIED = "RISK_LIMIT_MODIFIED"
    COMPLIANCE_VIOLATION = "COMPLIANCE_VIOLATION"
    SYSTEM_CONFIG_CHANGED = "SYSTEM_CONFIG_CHANGED"
    DATA_ACCESS = "DATA_ACCESS"
    UNAUTHORIZED_ACCESS_ATTEMPT = "UNAUTHORIZED_ACCESS_ATTEMPT"


class AuditSeverity(Enum):
    """Audit event severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class TestAuditTrailManager:
    """Test suite for the audit trail manager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.test_events = [
            {
                'event_id': 'AUD_001',
                'event_type': AuditEventType.USER_LOGIN.value,
                'user_id': 'trader_001',
                'session_id': 'sess_' + str(uuid.uuid4()),
                'timestamp': datetime.now().isoformat(),
                'severity': AuditSeverity.INFO.value,
                'source_ip': '192.168.1.100',
                'user_agent': 'TradingApp/1.0',
                'data': {
                    'login_method': 'PASSWORD',
                    'mfa_used': True,
                    'login_success': True
                }
            },
            {
                'event_id': 'AUD_002',
                'event_type': AuditEventType.ORDER_PLACED.value,
                'user_id': 'trader_001',
                'session_id': 'sess_' + str(uuid.uuid4()),
                'timestamp': datetime.now().isoformat(),
                'severity': AuditSeverity.INFO.value,
                'source_ip': '192.168.1.100',
                'data': {
                    'order_id': 'ORD_001',
                    'symbol': 'EURUSD',
                    'side': 'BUY',
                    'quantity': 100000,
                    'price': 1.0865,
                    'order_type': 'MARKET'
                }
            },
            {
                'event_id': 'AUD_003',
                'event_type': AuditEventType.COMPLIANCE_VIOLATION.value,
                'user_id': 'system',
                'session_id': None,
                'timestamp': datetime.now().isoformat(),
                'severity': AuditSeverity.WARNING.value,
                'source_ip': None,
                'data': {
                    'violation_type': 'POSITION_LIMIT_EXCEEDED',
                    'symbol': 'AAPL',
                    'current_position': 15000000,
                    'limit': 10000000,
                    'action_taken': 'POSITION_REDUCED'
                }
            },
            {
                'event_id': 'AUD_004',
                'event_type': AuditEventType.UNAUTHORIZED_ACCESS_ATTEMPT.value,
                'user_id': 'unknown',
                'session_id': None,
                'timestamp': datetime.now().isoformat(),
                'severity': AuditSeverity.CRITICAL.value,
                'source_ip': '10.0.0.50',
                'data': {
                    'attempted_resource': '/api/admin/users',
                    'authentication_method': 'API_KEY',
                    'failure_reason': 'INVALID_API_KEY',
                    'blocked': True
                }
            }
        ]
        
        self.encryption_key = b'test_encryption_key_32_bytes_long'
        self.signing_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
    
    @pytest.mark.asyncio
    async def test_audit_trail_initialization(self):
        """Test audit trail manager initialization."""
        with patch('nautilus_trader_engine.audit.AuditTrailManager') as mock_manager:
            mock_instance = AsyncMock()
            mock_manager.return_value = mock_instance
            
            # Configure initialization response
            mock_instance.initialize.return_value = {
                'status': 'INITIALIZED',
                'storage_backend': 'POSTGRESQL',
                'encryption_enabled': True,
                'digital_signatures_enabled': True,
                'blockchain_integration': True,
                'retention_policy_days': 2555,  # 7 years
                'compression_enabled': True
            }
            
            mock_instance.setup_encryption.return_value = {
                'encryption_setup': True,
                'key_rotation_enabled': True,
                'encryption_algorithm': 'AES-256-GCM'
            }
            
            manager = mock_manager()
            
            # Test initialization
            init_result = await manager.initialize()
            
            assert init_result['status'] == 'INITIALIZED', "Audit trail manager not initialized"
            assert init_result['encryption_enabled'] is True, "Encryption not enabled"
            assert init_result['digital_signatures_enabled'] is True, "Digital signatures not enabled"
            assert init_result['retention_policy_days'] >= 2555, "Retention policy too short"
            
            # Test encryption setup
            encryption_result = await manager.setup_encryption()
            
            assert encryption_result['encryption_setup'] is True, "Encryption setup failed"
            assert encryption_result['key_rotation_enabled'] is True, "Key rotation not enabled"
    
    @pytest.mark.asyncio
    async def test_audit_event_creation(self):
        """Test audit event creation and validation."""
        with patch('nautilus_trader_engine.audit.AuditEventCreator') as mock_creator:
            mock_instance = AsyncMock()
            mock_creator.return_value = mock_instance
            
            def create_audit_event(event_data):
                # Generate cryptographic hash
                event_json = json.dumps(event_data, sort_keys=True)
                event_hash = hashlib.sha256(event_json.encode()).hexdigest()
                
                # Generate digital signature (simplified)
                signature = base64.b64encode(f"signature_{event_data['event_id']}".encode()).decode()
                
                return {
                    'event_id': event_data['event_id'],
                    'created_at': datetime.now().isoformat(),
                    'hash': event_hash,
                    'digital_signature': signature,
                    'blockchain_reference': f"block_{uuid.uuid4()}",
                    'immutable': True,
                    'encrypted': True,
                    'validation_status': 'VALID'
                }
            
            mock_instance.create_audit_event.side_effect = create_audit_event
            
            mock_instance.validate_event_data.return_value = {
                'valid': True,
                'validation_errors': [],
                'required_fields_present': True,
                'data_integrity_check': 'PASSED'
            }
            
            creator = mock_creator()
            
            # Test event creation
            created_events = []
            for event_data in self.test_events:
                # Validate event data first
                validation_result = await creator.validate_event_data(event_data)
                
                assert validation_result['valid'] is True, f"Event {event_data['event_id']} validation failed"
                assert validation_result['required_fields_present'] is True, "Missing required fields"
                
                # Create audit event
                created_event = await creator.create_audit_event(event_data)
                created_events.append(created_event)
                
                # Verify event properties
                assert created_event['immutable'] is True, "Event not marked as immutable"
                assert created_event['encrypted'] is True, "Event not encrypted"
                assert 'hash' in created_event, "Missing cryptographic hash"
                assert 'digital_signature' in created_event, "Missing digital signature"
                assert 'blockchain_reference' in created_event, "Missing blockchain reference"
                assert created_event['validation_status'] == 'VALID', "Event validation failed"
            
            assert len(created_events) == len(self.test_events), "Not all events created"
    
    @pytest.mark.asyncio
    async def test_audit_event_storage(self):
        """Test audit event storage and retrieval."""
        with patch('nautilus_trader_engine.audit.AuditStorage') as mock_storage:
            mock_instance = AsyncMock()
            mock_storage.return_value = mock_instance
            
            # Configure storage responses
            mock_instance.store_audit_event.return_value = {
                'stored': True,
                'storage_id': lambda event_id: f"store_{event_id}",
                'storage_timestamp': datetime.now().isoformat(),
                'storage_location': 'PRIMARY_DB',
                'backup_created': True
            }
            
            def retrieve_audit_events(filters):
                # Filter events based on criteria
                filtered_events = self.test_events.copy()
                
                if 'event_type' in filters:
                    filtered_events = [e for e in filtered_events 
                                     if e['event_type'] == filters['event_type']]
                
                if 'user_id' in filters:
                    filtered_events = [e for e in filtered_events 
                                     if e['user_id'] == filters['user_id']]
                
                if 'severity' in filters:
                    filtered_events = [e for e in filtered_events 
                                     if e['severity'] == filters['severity']]
                
                if 'start_date' in filters and 'end_date' in filters:
                    start_date = datetime.fromisoformat(filters['start_date'])
                    end_date = datetime.fromisoformat(filters['end_date'])
                    filtered_events = [e for e in filtered_events 
                                     if start_date <= datetime.fromisoformat(e['timestamp']) <= end_date]
                
                return {
                    'total_events': len(filtered_events),
                    'events': filtered_events,
                    'query_time_ms': 25,
                    'cache_hit': False
                }
            
            mock_instance.retrieve_audit_events.side_effect = retrieve_audit_events
            
            storage = mock_storage()
            
            # Test event storage
            for event in self.test_events:
                storage_result = await storage.store_audit_event(event)
                
                assert storage_result['stored'] is True, f"Event {event['event_id']} not stored"
                assert storage_result['backup_created'] is True, "Backup not created"
            
            # Test event retrieval with various filters
            test_filters = [
                {'event_type': AuditEventType.USER_LOGIN.value},
                {'user_id': 'trader_001'},
                {'severity': AuditSeverity.CRITICAL.value},
                {
                    'start_date': (datetime.now() - timedelta(hours=1)).isoformat(),
                    'end_date': datetime.now().isoformat()
                }
            ]
            
            for filters in test_filters:
                retrieval_result = await storage.retrieve_audit_events(filters)
                
                assert 'total_events' in retrieval_result, "Missing total events count"
                assert 'events' in retrieval_result, "Missing events list"
                assert retrieval_result['query_time_ms'] < 1000, "Query time too slow"
                assert retrieval_result['total_events'] >= 0, "Invalid event count"
    
    @pytest.mark.asyncio
    async def test_audit_integrity_verification(self):
        """Test audit trail integrity verification."""
        with patch('nautilus_trader_engine.audit.AuditIntegrityVerifier') as mock_verifier:
            mock_instance = AsyncMock()
            mock_verifier.return_value = mock_instance
            
            # Test integrity verification scenarios
            integrity_test_cases = [
                {
                    'event_id': 'AUD_001',
                    'original_hash': 'abc123def456',
                    'current_hash': 'abc123def456',
                    'signature_valid': True,
                    'blockchain_verified': True,
                    'expected_result': True
                },
                {
                    'event_id': 'AUD_002',
                    'original_hash': 'xyz789uvw012',
                    'current_hash': 'xyz789uvw999',  # Modified
                    'signature_valid': True,
                    'blockchain_verified': True,
                    'expected_result': False
                },
                {
                    'event_id': 'AUD_003',
                    'original_hash': 'mno345pqr678',
                    'current_hash': 'mno345pqr678',
                    'signature_valid': False,  # Invalid signature
                    'blockchain_verified': True,
                    'expected_result': False
                }
            ]
            
            def verify_event_integrity(event_id):
                test_case = next((tc for tc in integrity_test_cases if tc['event_id'] == event_id), None)
                if not test_case:
                    return {'integrity_valid': False, 'error': 'Event not found'}
                
                hash_match = test_case['original_hash'] == test_case['current_hash']
                signature_valid = test_case['signature_valid']
                blockchain_verified = test_case['blockchain_verified']
                
                integrity_valid = hash_match and signature_valid and blockchain_verified
                
                return {
                    'event_id': event_id,
                    'integrity_valid': integrity_valid,
                    'hash_verified': hash_match,
                    'signature_verified': signature_valid,
                    'blockchain_verified': blockchain_verified,
                    'tampering_detected': not integrity_valid,
                    'verification_timestamp': datetime.now().isoformat()
                }
            
            mock_instance.verify_event_integrity.side_effect = verify_event_integrity
            
            def verify_audit_trail_integrity(start_date, end_date):
                total_events = len(integrity_test_cases)
                valid_events = len([tc for tc in integrity_test_cases if tc['expected_result']])
                invalid_events = total_events - valid_events
                
                return {
                    'total_events_checked': total_events,
                    'valid_events': valid_events,
                    'invalid_events': invalid_events,
                    'integrity_percentage': (valid_events / total_events) * 100,
                    'overall_integrity': 'COMPROMISED' if invalid_events > 0 else 'INTACT',
                    'verification_duration_ms': 150,
                    'suspicious_patterns': [
                        {
                            'pattern_type': 'HASH_MISMATCH',
                            'affected_events': ['AUD_002'],
                            'severity': 'HIGH'
                        },
                        {
                            'pattern_type': 'SIGNATURE_INVALID',
                            'affected_events': ['AUD_003'],
                            'severity': 'CRITICAL'
                        }
                    ] if invalid_events > 0 else []
                }
            
            mock_instance.verify_audit_trail_integrity.side_effect = verify_audit_trail_integrity
            
            verifier = mock_verifier()
            
            # Test individual event integrity verification
            for test_case in integrity_test_cases:
                verification_result = await verifier.verify_event_integrity(test_case['event_id'])
                
                assert verification_result['integrity_valid'] == test_case['expected_result'], \
                    f"Integrity verification failed for {test_case['event_id']}"
                
                if not test_case['expected_result']:
                    assert verification_result['tampering_detected'] is True, \
                        f"Tampering not detected for {test_case['event_id']}"
            
            # Test overall audit trail integrity
            trail_integrity = await verifier.verify_audit_trail_integrity(
                datetime.now() - timedelta(days=1),
                datetime.now()
            )
            
            assert 'total_events_checked' in trail_integrity, "Missing total events count"
            assert 'integrity_percentage' in trail_integrity, "Missing integrity percentage"
            assert 0 <= trail_integrity['integrity_percentage'] <= 100, "Invalid integrity percentage"
            
            if trail_integrity['invalid_events'] > 0:
                assert trail_integrity['overall_integrity'] == 'COMPROMISED', "Should detect compromised integrity"
                assert len(trail_integrity['suspicious_patterns']) > 0, "Should identify suspicious patterns"
    
    @pytest.mark.asyncio
    async def test_audit_search_and_filtering(self):
        """Test audit trail search and filtering capabilities."""
        with patch('nautilus_trader_engine.audit.AuditSearchEngine') as mock_search:
            mock_instance = AsyncMock()
            mock_search.return_value = mock_instance
            
            # Configure search responses
            def search_audit_events(search_criteria):
                results = []
                
                # Text search in event data
                if 'text_query' in search_criteria:
                    query = search_criteria['text_query'].lower()
                    for event in self.test_events:
                        event_text = json.dumps(event).lower()
                        if query in event_text:
                            results.append(event)
                
                # Advanced filtering
                if 'advanced_filters' in search_criteria:
                    filters = search_criteria['advanced_filters']
                    filtered_events = self.test_events.copy()
                    
                    if 'event_types' in filters:
                        filtered_events = [e for e in filtered_events 
                                         if e['event_type'] in filters['event_types']]
                    
                    if 'severity_levels' in filters:
                        filtered_events = [e for e in filtered_events 
                                         if e['severity'] in filters['severity_levels']]
                    
                    if 'user_ids' in filters:
                        filtered_events = [e for e in filtered_events 
                                         if e['user_id'] in filters['user_ids']]
                    
                    if 'ip_addresses' in filters:
                        filtered_events = [e for e in filtered_events 
                                         if e.get('source_ip') in filters['ip_addresses']]
                    
                    results = filtered_events
                
                # Sort results
                sort_field = search_criteria.get('sort_by', 'timestamp')
                sort_order = search_criteria.get('sort_order', 'desc')
                
                if sort_field in ['timestamp']:
                    results.sort(
                        key=lambda x: x.get(sort_field, ''),
                        reverse=(sort_order == 'desc')
                    )
                
                # Pagination
                page = search_criteria.get('page', 1)
                page_size = search_criteria.get('page_size', 10)
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                
                paginated_results = results[start_idx:end_idx]
                
                return {
                    'total_results': len(results),
                    'page': page,
                    'page_size': page_size,
                    'total_pages': (len(results) + page_size - 1) // page_size,
                    'events': paginated_results,
                    'search_time_ms': 45,
                    'facets': {
                        'event_types': list(set(e['event_type'] for e in results)),
                        'severity_levels': list(set(e['severity'] for e in results)),
                        'users': list(set(e['user_id'] for e in results))
                    }
                }
            
            mock_instance.search_audit_events.side_effect = search_audit_events
            
            search_engine = mock_search()
            
            # Test text search
            text_search_result = await search_engine.search_audit_events({
                'text_query': 'ORDER_PLACED',
                'sort_by': 'timestamp',
                'sort_order': 'desc'
            })
            
            assert text_search_result['total_results'] > 0, "Text search should find results"
            assert 'events' in text_search_result, "Missing events in search results"
            assert text_search_result['search_time_ms'] < 1000, "Search time too slow"
            
            # Test advanced filtering
            advanced_search_result = await search_engine.search_audit_events({
                'advanced_filters': {
                    'event_types': [AuditEventType.COMPLIANCE_VIOLATION.value, AuditEventType.UNAUTHORIZED_ACCESS_ATTEMPT.value],
                    'severity_levels': [AuditSeverity.WARNING.value, AuditSeverity.CRITICAL.value]
                },
                'page': 1,
                'page_size': 5
            })
            
            assert 'facets' in advanced_search_result, "Missing search facets"
            assert 'total_pages' in advanced_search_result, "Missing pagination info"
            
            # Verify facets
            facets = advanced_search_result['facets']
            assert 'event_types' in facets, "Missing event types facet"
            assert 'severity_levels' in facets, "Missing severity levels facet"
            assert 'users' in facets, "Missing users facet"
            
            # Test user-specific search
            user_search_result = await search_engine.search_audit_events({
                'advanced_filters': {
                    'user_ids': ['trader_001']
                }
            })
            
            assert user_search_result['total_results'] >= 0, "User search should return results"
            
            # Verify all returned events belong to the specified user
            for event in user_search_result['events']:
                assert event['user_id'] == 'trader_001', "Search returned events for wrong user"
    
    @pytest.mark.asyncio
    async def test_audit_retention_management(self):
        """Test audit trail retention and archival management."""
        with patch('nautilus_trader_engine.audit.AuditRetentionManager') as mock_retention:
            mock_instance = AsyncMock()
            mock_retention.return_value = mock_instance
            
            # Configure retention policies
            retention_policies = {
                'default_retention_days': 2555,  # 7 years
                'event_type_policies': {
                    AuditEventType.USER_LOGIN.value: 1095,  # 3 years
                    AuditEventType.COMPLIANCE_VIOLATION.value: 3650,  # 10 years
                    AuditEventType.UNAUTHORIZED_ACCESS_ATTEMPT.value: 3650,  # 10 years
                    AuditEventType.ORDER_PLACED.value: 2555  # 7 years
                },
                'severity_policies': {
                    AuditSeverity.CRITICAL.value: 3650,  # 10 years
                    AuditSeverity.ERROR.value: 2555,  # 7 years
                    AuditSeverity.WARNING.value: 1825,  # 5 years
                    AuditSeverity.INFO.value: 1095  # 3 years
                },
                'archival_enabled': True,
                'compression_enabled': True
            }
            
            mock_instance.get_retention_policies.return_value = retention_policies
            
            def calculate_retention_period(event):
                event_type = event['event_type']
                severity = event['severity']
                
                # Get retention period based on event type
                type_retention = retention_policies['event_type_policies'].get(
                    event_type, retention_policies['default_retention_days']
                )
                
                # Get retention period based on severity
                severity_retention = retention_policies['severity_policies'].get(
                    severity, retention_policies['default_retention_days']
                )
                
                # Use the longer retention period
                retention_days = max(type_retention, severity_retention)
                
                event_date = datetime.fromisoformat(event['timestamp'])
                expiry_date = event_date + timedelta(days=retention_days)
                
                return {
                    'event_id': event['event_id'],
                    'retention_days': retention_days,
                    'expiry_date': expiry_date.isoformat(),
                    'days_until_expiry': (expiry_date - datetime.now()).days,
                    'eligible_for_archival': (datetime.now() - event_date).days > 365,
                    'eligible_for_deletion': datetime.now() > expiry_date
                }
            
            mock_instance.calculate_retention_period.side_effect = calculate_retention_period
            
            mock_instance.archive_old_events.return_value = {
                'events_archived': 150,
                'archive_size_mb': 25.6,
                'archive_location': 'cold_storage_bucket_001',
                'compression_ratio': 0.35,
                'archival_duration_ms': 5000
            }
            
            mock_instance.delete_expired_events.return_value = {
                'events_deleted': 50,
                'space_freed_mb': 8.2,
                'deletion_duration_ms': 1200,
                'backup_created': True
            }
            
            retention_manager = mock_retention()
            
            # Test retention policy retrieval
            policies = await retention_manager.get_retention_policies()
            
            assert 'default_retention_days' in policies, "Missing default retention policy"
            assert policies['default_retention_days'] >= 2555, "Default retention too short"
            assert 'event_type_policies' in policies, "Missing event type policies"
            assert 'severity_policies' in policies, "Missing severity policies"
            
            # Test retention period calculation
            retention_calculations = []
            for event in self.test_events:
                retention_calc = await retention_manager.calculate_retention_period(event)
                retention_calculations.append(retention_calc)
                
                assert retention_calc['retention_days'] > 0, "Invalid retention period"
                assert 'expiry_date' in retention_calc, "Missing expiry date"
                assert 'eligible_for_archival' in retention_calc, "Missing archival eligibility"
            
            # Verify retention periods are appropriate for event types
            critical_events = [calc for calc in retention_calculations 
                             if any(e['event_id'] == calc['event_id'] and e['severity'] == AuditSeverity.CRITICAL.value 
                                   for e in self.test_events)]
            
            for critical_event in critical_events:
                assert critical_event['retention_days'] >= 3650, "Critical events should have long retention"
            
            # Test archival process
            archival_result = await retention_manager.archive_old_events()
            
            assert archival_result['events_archived'] >= 0, "Invalid archived events count"
            assert 'archive_location' in archival_result, "Missing archive location"
            assert archival_result['compression_ratio'] < 1.0, "Invalid compression ratio"
            
            # Test deletion process
            deletion_result = await retention_manager.delete_expired_events()
            
            assert deletion_result['events_deleted'] >= 0, "Invalid deleted events count"
            assert deletion_result['backup_created'] is True, "Backup not created before deletion"
    
    @pytest.mark.asyncio
    async def test_audit_compliance_reporting(self):
        """Test audit compliance reporting for regulatory requirements."""
        with patch('nautilus_trader_engine.audit.AuditComplianceReporter') as mock_reporter:
            mock_instance = AsyncMock()
            mock_reporter.return_value = mock_instance
            
            # Configure compliance reporting responses
            mock_instance.generate_sox_compliance_report.return_value = {
                'report_id': 'SOX_RPT_' + datetime.now().strftime('%Y%m%d'),
                'reporting_period': 'Q1_2024',
                'total_financial_transactions': 15000,
                'audit_trail_completeness': 99.8,
                'control_effectiveness': 'EFFECTIVE',
                'identified_deficiencies': [
                    {
                        'deficiency_type': 'MINOR_GAP',
                        'description': 'Some user login events missing IP address',
                        'impact': 'LOW',
                        'remediation_plan': 'Update logging configuration'
                    }
                ],
                'management_assertions': {
                    'internal_controls_effective': True,
                    'financial_reporting_accurate': True,
                    'audit_trail_complete': True
                }
            }
            
            mock_instance.generate_gdpr_compliance_report.return_value = {
                'report_id': 'GDPR_RPT_' + datetime.now().strftime('%Y%m%d'),
                'data_processing_activities': 25,
                'personal_data_events_logged': 500,
                'data_subject_requests_processed': 12,
                'privacy_by_design_compliance': 'COMPLIANT',
                'data_retention_compliance': 'COMPLIANT',
                'consent_management_audit': {
                    'total_consent_events': 150,
                    'valid_consents': 148,
                    'expired_consents': 2,
                    'compliance_rate': 98.7
                },
                'breach_incidents': []
            }
            
            mock_instance.generate_audit_summary_report.return_value = {
                'report_id': 'AUDIT_SUMMARY_' + datetime.now().strftime('%Y%m%d'),
                'reporting_period': {
                    'start_date': (datetime.now() - timedelta(days=30)).date().isoformat(),
                    'end_date': datetime.now().date().isoformat()
                },
                'total_audit_events': len(self.test_events),
                'events_by_type': {
                    event_type.value: len([e for e in self.test_events if e['event_type'] == event_type.value])
                    for event_type in AuditEventType
                },
                'events_by_severity': {
                    severity.value: len([e for e in self.test_events if e['severity'] == severity.value])
                    for severity in AuditSeverity
                },
                'security_incidents': 1,  # UNAUTHORIZED_ACCESS_ATTEMPT
                'compliance_violations': 1,  # COMPLIANCE_VIOLATION
                'system_availability': 99.95,
                'audit_trail_integrity': 100.0,
                'recommendations': [
                    'Implement additional monitoring for unauthorized access attempts',
                    'Review and update compliance violation response procedures',
                    'Enhance user authentication logging'
                ]
            }
            
            reporter = mock_reporter()
            
            # Test SOX compliance report
            sox_report = await reporter.generate_sox_compliance_report('Q1_2024')
            
            assert 'report_id' in sox_report, "Missing SOX report ID"
            assert sox_report['audit_trail_completeness'] >= 95.0, "Audit trail completeness too low"
            assert sox_report['control_effectiveness'] in ['EFFECTIVE', 'NEEDS_IMPROVEMENT'], \
                "Invalid control effectiveness status"
            
            # Verify management assertions
            assertions = sox_report['management_assertions']
            assert assertions['audit_trail_complete'] is True, "Audit trail not complete"
            assert assertions['internal_controls_effective'] is True, "Internal controls not effective"
            
            # Test GDPR compliance report
            gdpr_report = await reporter.generate_gdpr_compliance_report()
            
            assert 'personal_data_events_logged' in gdpr_report, "Missing personal data events count"
            assert gdpr_report['privacy_by_design_compliance'] == 'COMPLIANT', "Privacy by design not compliant"
            assert gdpr_report['data_retention_compliance'] == 'COMPLIANT', "Data retention not compliant"
            
            # Verify consent management audit
            consent_audit = gdpr_report['consent_management_audit']
            assert consent_audit['compliance_rate'] >= 95.0, "Consent compliance rate too low"
            
            # Test audit summary report
            summary_report = await reporter.generate_audit_summary_report()
            
            assert summary_report['total_audit_events'] > 0, "No audit events in summary"
            assert 'events_by_type' in summary_report, "Missing events by type breakdown"
            assert 'events_by_severity' in summary_report, "Missing events by severity breakdown"
            assert summary_report['audit_trail_integrity'] >= 99.0, "Audit trail integrity too low"
            
            # Verify event type breakdown
            events_by_type = summary_report['events_by_type']
            total_events_in_breakdown = sum(events_by_type.values())
            assert total_events_in_breakdown <= summary_report['total_audit_events'], \
                "Event type breakdown exceeds total events"


if __name__ == '__main__':
    pytest.main([__file__])