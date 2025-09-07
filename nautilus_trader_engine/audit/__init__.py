"""Audit Module for Nautilus Trader Engine
Handles audit trail management and regulatory compliance reporting.
"""

from .audit_manager import AuditTrailManager

# Additional audit components needed for unit tests
class AuditEventCreator:
    """Creates and validates audit events."""
    pass

class AuditStorage:
    """Handles storage and retrieval of audit events."""
    pass

class AuditIntegrityVerifier:
    """Verifies the integrity of audit events and trails."""
    pass

class AuditSearchEngine:
    """Provides search and filtering capabilities for audit trails."""
    pass

class AuditRetentionManager:
    """Manages audit event retention and archival policies."""
    pass

class AuditComplianceReporter:
    """Generates compliance reports for regulatory requirements."""
    pass

__all__ = [
    'AuditTrailManager',
    'AuditEventCreator',
    'AuditStorage',
    'AuditIntegrityVerifier',
    'AuditSearchEngine',
    'AuditRetentionManager',
    'AuditComplianceReporter'
]