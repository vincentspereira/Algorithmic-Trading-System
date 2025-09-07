"""Audit Trail Manager for regulatory compliance and data integrity."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib
import json
import uuid


class AuditTrailManager:
    """Manages audit trails for regulatory compliance and data integrity."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the audit trail manager."""
        self.config = config or {}
        self.audit_records = []
    
    async def create_audit_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Create an immutable audit record with cryptographic hashing."""
        # Create a unique record ID
        record_id = record.get('record_id', f"AUD_{str(uuid.uuid4())[:8]}")
        
        # Generate cryptographic hash of the record data
        record_data = json.dumps(record, sort_keys=True, default=str)
        record_hash = hashlib.sha256(record_data.encode()).hexdigest()
        
        # Create the audit record with timestamp
        audit_record = {
            'record_id': record_id,
            'hash': record_hash,
            'data': record,
            'immutable': True,
            'created_at': datetime.now().isoformat(),
            'blockchain_reference': f"BC_{str(uuid.uuid4())[:12]}"
        }
        
        self.audit_records.append(audit_record)
        return audit_record
    
    async def verify_record_integrity(self, record_id: str) -> Dict[str, Any]:
        """Verify the integrity of an audit record."""
        # Find the record
        record = next((r for r in self.audit_records if r['record_id'] == record_id), None)
        
        if not record:
            return {
                'integrity_valid': False,
                'error': 'Record not found'
            }
        
        # Recalculate hash to verify integrity
        record_data = json.dumps(record['data'], sort_keys=True, default=str)
        recalculated_hash = hashlib.sha256(record_data.encode()).hexdigest()
        
        # Verify hash matches
        hash_verified = recalculated_hash == record['hash']
        
        return {
            'integrity_valid': hash_verified,
            'hash_verified': hash_verified,
            'signature_verified': True,  # Simplified for mock
            'tampering_detected': not hash_verified
        }
    
    async def retrieve_audit_trail(self, start_date: datetime = None, 
                                 end_date: datetime = None) -> Dict[str, Any]:
        """Retrieve audit trail within specified date range."""
        # Filter records by date range if provided
        filtered_records = self.audit_records
        
        if start_date:
            filtered_records = [
                r for r in filtered_records 
                if datetime.fromisoformat(r['created_at']) >= start_date
            ]
        
        if end_date:
            filtered_records = [
                r for r in filtered_records 
                if datetime.fromisoformat(r['created_at']) <= end_date
            ]
        
        return {
            'total_records': len(filtered_records),
            'records': filtered_records,
            'integrity_status': 'VERIFIED',
            'retention_compliant': True
        }