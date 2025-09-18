"""
STRIDE Threat Modeling Service for Algorithmic Trading System

Implements Microsoft's STRIDE methodology for threat modeling:
- Spoofing
- Tampering
- Repudiation
- Information Disclosure
- Denial of Service
- Elevation of Privilege

Author: Vincent S. Pereira
Version: 1.0.0
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from enum import Enum
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ThreatCategory(Enum):
    """STRIDE threat categories"""
    SPOOFING = "Spoofing"
    TAMPERING = "Tampering"
    REPUDIATION = "Repudiation"
    INFORMATION_DISCLOSURE = "Information Disclosure"
    DENIAL_OF_SERVICE = "Denial of Service"
    ELEVATION_OF_PRIVILEGE = "Elevation of Privilege"

class ThreatSeverity(Enum):
    """Threat severity levels"""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class ThreatModel(BaseModel):
    """Model for individual threat"""
    id: str
    component: str
    category: ThreatCategory
    description: str
    severity: ThreatSeverity
    mitigation: str
    affected_assets: List[str]
    cvss_score: float
    discovered_date: datetime
    status: str = "Open"  # Open, Mitigated, Accepted, False Positive

class ComponentThreatModel(BaseModel):
    """Model for component-level threat model"""
    component_name: str
    component_type: str
    threats: List[ThreatModel]
    overall_risk_score: float
    last_updated: datetime
    version: str

class SystemThreatModel(BaseModel):
    """Model for system-level threat model"""
    system_name: str
    components: List[ComponentThreatModel]
    overall_risk_score: float
    critical_threats: int
    high_threats: int
    medium_threats: int
    low_threats: int
    last_updated: datetime
    version: str

class STRIDEThreatModelingService:
    """Service for performing STRIDE threat modeling"""
    
    def __init__(self):
        self.threat_patterns = self._load_threat_patterns()
        
    def _load_threat_patterns(self) -> Dict:
        """Load predefined threat patterns for common components"""
        # These are example patterns - in a real implementation, these would be more comprehensive
        return {
            "API Gateway": {
                ThreatCategory.SPOOFING: {
                    "description": "Unauthorized entities attempting to impersonate legitimate users",
                    "mitigation": "Implement OAuth 2.0/OIDC with JWT tokens, enforce MFA, use mutual TLS",
                    "severity": ThreatSeverity.HIGH,
                    "cvss_base": 7.5
                },
                ThreatCategory.DENIAL_OF_SERVICE: {
                    "description": "Overwhelming the API gateway with requests to make it unavailable",
                    "mitigation": "Implement rate limiting, request throttling, DDoS protection services",
                    "severity": ThreatSeverity.HIGH,
                    "cvss_base": 7.0
                },
                ThreatCategory.TAMPERING: {
                    "description": "Modification of data in transit between client and gateway",
                    "mitigation": "Enforce TLS 1.3 encryption, implement message signing, use API gateways with built-in validation",
                    "severity": ThreatSeverity.MEDIUM,
                    "cvss_base": 5.5
                }
            },
            "Trading Engine": {
                ThreatCategory.TAMPERING: {
                    "description": "Unauthorized modification of trade orders or execution parameters",
                    "mitigation": "Implement immutable event sourcing, digital signatures for all trade events, audit trails",
                    "severity": ThreatSeverity.CRITICAL,
                    "cvss_base": 9.0
                },
                ThreatCategory.REPUDIATION: {
                    "description": "Traders denying placing orders or system denying executing trades",
                    "mitigation": "Implement comprehensive audit logging, digital signatures, non-repudiation protocols",
                    "severity": ThreatSeverity.HIGH,
                    "cvss_base": 7.0
                },
                ThreatCategory.INFORMATION_DISCLOSURE: {
                    "description": "Unauthorized access to sensitive trading data or strategies",
                    "mitigation": "Implement RBAC, encrypt data at rest and in transit, use secure enclaves for sensitive computations",
                    "severity": ThreatSeverity.HIGH,
                    "cvss_base": 7.5
                }
            },
            "Database": {
                ThreatCategory.INFORMATION_DISCLOSURE: {
                    "description": "Unauthorized access to sensitive financial data, trade history, or user information",
                    "mitigation": "Implement AES-256 encryption at rest, TLS 1.3 for data in transit, RBAC with least privilege",
                    "severity": ThreatSeverity.CRITICAL,
                    "cvss_base": 9.0
                },
                ThreatCategory.TAMPERING: {
                    "description": "Unauthorized modification of stored data including trade records or user accounts",
                    "mitigation": "Implement database auditing, checksums, immutable logs with Apache Iceberg",
                    "severity": ThreatSeverity.HIGH,
                    "cvss_base": 7.0
                },
                ThreatCategory.DENIAL_OF_SERVICE: {
                    "description": "Overwhelming database with queries to make it unavailable",
                    "mitigation": "Implement query rate limiting, connection pooling, database load balancing",
                    "severity": ThreatSeverity.MEDIUM,
                    "cvss_base": 5.5
                }
            },
            "Message Queue (Kafka)": {
                ThreatCategory.TAMPERING: {
                    "description": "Modification of messages in the queue or during transmission",
                    "mitigation": "Implement message signing, Schema Registry with schema validation, TLS encryption",
                    "severity": ThreatSeverity.HIGH,
                    "cvss_base": 7.0
                },
                ThreatCategory.REPUDIATION: {
                    "description": "Producers/consumers denying sending/receiving messages",
                    "mitigation": "Implement message tracing, digital signatures, comprehensive audit logs",
                    "severity": ThreatSeverity.MEDIUM,
                    "cvss_base": 5.5
                },
                ThreatCategory.DENIAL_OF_SERVICE: {
                    "description": "Overwhelming Kafka brokers with messages or connections",
                    "mitigation": "Implement producer/consumer quotas, network partitioning, load balancing",
                    "severity": ThreatSeverity.MEDIUM,
                    "cvss_base": 5.0
                }
            },
            "Authentication Service": {
                ThreatCategory.SPOOFING: {
                    "description": "Impersonation of legitimate users to gain unauthorized access",
                    "mitigation": "Implement OAuth 2.0/OIDC with JWT, enforce MFA, use biometric authentication",
                    "severity": ThreatSeverity.CRITICAL,
                    "cvss_base": 9.0
                },
                ThreatCategory.REPUDIATION: {
                    "description": "Users denying authentication actions",
                    "mitigation": "Implement comprehensive audit logging, session management, non-repudiation protocols",
                    "severity": ThreatSeverity.MEDIUM,
                    "cvss_base": 5.5
                }
            }
        }
    
    def model_component_threats(self, component_name: str, component_type: str) -> ComponentThreatModel:
        """Generate threat model for a specific component"""
        threats = []
        risk_score = 0.0
        threat_count = 0
        
        # Get threat patterns for this component type
        patterns = self.threat_patterns.get(component_type, {})
        
        # Apply each threat pattern
        for category, pattern in patterns.items():
            threat_id = f"THREAT-{component_name.upper()}-{category.name}-{threat_count+1:03d}"
            
            threat = ThreatModel(
                id=threat_id,
                component=component_name,
                category=category,
                description=pattern["description"],
                severity=pattern["severity"],
                mitigation=pattern["mitigation"],
                affected_assets=[component_name],
                cvss_score=pattern["cvss_base"],
                discovered_date=datetime.now(timezone.utc)
            )
            
            threats.append(threat)
            risk_score += pattern["cvss_base"]
            threat_count += 1
        
        # Add some generic threats that apply to all components
        generic_threats = self._generate_generic_threats(component_name)
        threats.extend(generic_threats)
        risk_score += sum(t.cvss_score for t in generic_threats)
        
        overall_risk = risk_score / max(len(threats), 1) if threats else 0.0
        
        return ComponentThreatModel(
            component_name=component_name,
            component_type=component_type,
            threats=threats,
            overall_risk_score=overall_risk,
            last_updated=datetime.now(timezone.utc),
            version="1.0.0"
        )
    
    def _generate_generic_threats(self, component_name: str) -> List[ThreatModel]:
        """Generate generic threats that apply to all components"""
        generic_threats = []
        threat_count = 0
        
        # Generic threats
        generic_patterns = {
            ThreatCategory.INFORMATION_DISCLOSURE: {
                "description": "Accidental exposure of sensitive information through logs, error messages, or debugging interfaces",
                "mitigation": "Implement proper logging levels, sanitize error messages, use structured logging with PII filtering",
                "severity": ThreatSeverity.MEDIUM,
                "cvss_base": 5.0
            },
            ThreatCategory.DENIAL_OF_SERVICE: {
                "description": "Resource exhaustion through memory leaks, unhandled exceptions, or inefficient algorithms",
                "mitigation": "Implement proper error handling, resource limits, health checks, and auto-restart mechanisms",
                "severity": ThreatSeverity.MEDIUM,
                "cvss_base": 5.0
            }
        }
        
        for category, pattern in generic_patterns.items():
            threat_id = f"THREAT-{component_name.upper()}-{category.name}-GEN-{threat_count+1:03d}"
            
            threat = ThreatModel(
                id=threat_id,
                component=component_name,
                category=category,
                description=pattern["description"],
                severity=pattern["severity"],
                mitigation=pattern["mitigation"],
                affected_assets=[component_name],
                cvss_score=pattern["cvss_base"],
                discovered_date=datetime.now(timezone.utc)
            )
            
            generic_threats.append(threat)
            threat_count += 1
            
        return generic_threats
    
    def model_system_threats(self, system_components: List[Dict]) -> SystemThreatModel:
        """Generate comprehensive threat model for the entire system"""
        component_models = []
        total_risk = 0.0
        critical_count = 0
        high_count = 0
        medium_count = 0
        low_count = 0
        
        # Model threats for each component
        for component in system_components:
            component_name = component.get("name", "Unknown")
            component_type = component.get("type", "Generic")
            
            component_model = self.model_component_threats(component_name, component_type)
            component_models.append(component_model)
            
            total_risk += component_model.overall_risk_score
            
            # Count threats by severity
            for threat in component_model.threats:
                if threat.severity == ThreatSeverity.CRITICAL:
                    critical_count += 1
                elif threat.severity == ThreatSeverity.HIGH:
                    high_count += 1
                elif threat.severity == ThreatSeverity.MEDIUM:
                    medium_count += 1
                elif threat.severity == ThreatSeverity.LOW:
                    low_count += 1
        
        overall_risk = total_risk / max(len(component_models), 1) if component_models else 0.0
        
        return SystemThreatModel(
            system_name="Algorithmic Trading System",
            components=component_models,
            overall_risk_score=overall_risk,
            critical_threats=critical_count,
            high_threats=high_count,
            medium_threats=medium_count,
            low_threats=low_count,
            last_updated=datetime.now(timezone.utc),
            version="1.0.0"
        )
    
    def generate_threat_report(self, system_model: SystemThreatModel) -> str:
        """Generate a formatted threat modeling report"""
        report = []
        report.append("# STRIDE Threat Modeling Report")
        report.append(f"## System: {system_model.system_name}")
        report.append(f"## Generated: {system_model.last_updated.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        report.append(f"## Version: {system_model.version}")
        report.append("")
        report.append("## Summary")
        report.append(f"- Overall Risk Score: {system_model.overall_risk_score:.2f}/10.0")
        report.append(f"- Critical Threats: {system_model.critical_threats}")
        report.append(f"- High Threats: {system_model.high_threats}")
        report.append(f"- Medium Threats: {system_model.medium_threats}")
        report.append(f"- Low Threats: {system_model.low_threats}")
        report.append("")
        report.append("## Component Threat Models")
        
        for component in system_model.components:
            report.append(f"### {component.component_name} ({component.component_type})")
            report.append(f"- Risk Score: {component.overall_risk_score:.2f}/10.0")
            report.append("- Identified Threats:")
            
            for threat in component.threats:
                report.append(f"  - **{threat.category.value}** ({threat.severity.value})")
                report.append(f"    - Description: {threat.description}")
                report.append(f"    - Mitigation: {threat.mitigation}")
                report.append(f"    - CVSS Score: {threat.cvss_score}")
                report.append("")
        
        return "\n".join(report)
    
    def save_threat_model(self, system_model: SystemThreatModel, filepath: str):
        """Save threat model to JSON file"""
        try:
            with open(filepath, 'w') as f:
                json.dump(system_model.dict(), f, indent=2, default=str)
            logger.info(f"Threat model saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save threat model: {e}")
            raise

# Example usage
if __name__ == "__main__":
    # Define system components for threat modeling
    system_components = [
        {"name": "API Gateway", "type": "API Gateway"},
        {"name": "Trading Engine", "type": "Trading Engine"},
        {"name": "PostgreSQL Database", "type": "Database"},
        {"name": "Kafka Message Bus", "type": "Message Queue (Kafka)"},
        {"name": "Authentication Service", "type": "Authentication Service"}
    ]
    
    # Create threat modeling service
    stride_service = STRIDEThreatModelingService()
    
    # Generate system threat model
    system_model = stride_service.model_system_threats(system_components)
    
    # Generate and print report
    report = stride_service.generate_threat_report(system_model)
    print(report)
    
    # Save to file
    stride_service.save_threat_model(system_model, "stride_threat_model.json")