#!/usr/bin/env python3
"""
Automated STRIDE Threat Modeling Script
Generates threat models for the Algorithmic Trading System components.

This script is designed to be run as part of the GitHub Actions security scanning workflow.
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List

# Add the security service path to sys.path to import STRIDE modeling
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services', 'dependency_management_service', 'security_service'))

try:
    from stride_threat_modeling import STRIDEThreatModelingService
    print("✅ Successfully imported STRIDE threat modeling service")
except ImportError as e:
    print(f"❌ Failed to import STRIDE threat modeling service: {e}")
    print("Please ensure the security service is properly configured.")
    sys.exit(1)

def get_system_components() -> List[Dict]:
    """Define the system components for threat modeling."""
    return [
        {"name": "API Gateway", "type": "API Gateway"},
        {"name": "Trading Engine", "type": "Trading Engine"},
        {"name": "PostgreSQL Database", "type": "Database"},
        {"name": "Kafka Message Bus", "type": "Message Queue (Kafka)"},
        {"name": "Authentication Service", "type": "Authentication Service"},
        {"name": "Redis Cache", "type": "Database"},
        {"name": "ClickHouse Analytics", "type": "Database"},
        {"name": "Qdrant Vector Store", "type": "Database"},
        {"name": "Dependency Management Service", "type": "Microservice"},
        {"name": "Notification Service", "type": "Microservice"},
        {"name": "Security Service", "type": "Microservice"},
        {"name": "Monitoring Service", "type": "Microservice"},
        {"name": "Frontend Application", "type": "Web Application"},
        {"name": "Nautilus Trader Engine", "type": "Trading Engine"},
        {"name": "Iceberg Data Lake", "type": "Data Storage"},
        {"name": "InfluxDB Time Series", "type": "Database"},
        {"name": "Loki Log Storage", "type": "Database"},
        {"name": "Jaeger Tracing", "type": "Observability"},
        {"name": "Vault Secrets Management", "type": "Security Service"},
        {"name": "Prometheus Metrics", "type": "Observability"}
    ]

def main():
    """Main function to run automated threat modeling."""
    print("🔍 Running Automated STRIDE Threat Modeling Analysis...")
    print("=" * 60)
    
    try:
        # Initialize the STRIDE threat modeling service
        stride_service = STRIDEThreatModelingService()
        print("✅ STRIDE threat modeling service initialized")
        
        # Get system components
        system_components = get_system_components()
        print(f"📊 Analyzing {len(system_components)} system components")
        
        # Generate system threat model
        print("🔄 Generating threat model for all system components...")
        system_model = stride_service.model_system_threats(system_components)
        
        # Generate and save report
        print("📝 Generating threat modeling report...")
        report = stride_service.generate_threat_report(system_model)
        
        # Save to file
        report_path = os.path.join(os.path.dirname(__file__), "threat-model-report.txt")
        with open(report_path, 'w') as f:
            f.write(report)
        print(f"💾 Threat model report saved to: {report_path}")
        
        # Save JSON version
        json_path = os.path.join(os.path.dirname(__file__), "threat-model-report.json")
        with open(json_path, 'w') as f:
            json.dump(system_model.dict(), f, indent=2, default=str)
        print(f"💾 Threat model JSON saved to: {json_path}")
        
        # Print summary
        print("\n📊 Threat Modeling Summary:")
        print(f"  Overall Risk Score: {system_model.overall_risk_score:.2f}/10.0")
        print(f"  Critical Threats: {system_model.critical_threats}")
        print(f"  High Threats: {system_model.high_threats}")
        print(f"  Medium Threats: {system_model.medium_threats}")
        print(f"  Low Threats: {system_model.low_threats}")
        print(f"  Components Analyzed: {len(system_model.components)}")
        
        print("\n✅ Automated STRIDE threat modeling completed successfully!")
        return 0
        
    except Exception as e:
        print(f"❌ Error during threat modeling: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())