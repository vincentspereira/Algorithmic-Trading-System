#!/usr/bin/env python3
"""
Schema Registry Validator
Validates compatibility of Kafka-related dependencies with Schema Registry
for the Algorithmic Trading System.
"""

import requests
import json
import sys
import os
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime
+from datetime import datetime, timezone

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SchemaRegistryValidator:
    def __init__(self, schema_registry_url: str = None):
        self.schema_registry_url = schema_registry_url or os.getenv('SCHEMA_REGISTRY_URL', 'http://localhost:8081')
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/vnd.schemaregistry.v1+json'})
    
    def get_subjects(self) -> List[str]:
        """Get all subjects in Schema Registry."""
        try:
            response = self.session.get(f"{self.schema_registry_url}/subjects")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Error getting subjects: {e}")
        return []
    
    def get_schema_versions(self, subject: str) -> List[int]:
        """Get all versions of a schema subject."""
        try:
            response = self.session.get(f"{self.schema_registry_url}/subjects/{subject}/versions")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Error getting schema versions for {subject}: {e}")
        return []
    
    def get_schema_by_version(self, subject: str, version: int) -> Optional[Dict]:
        """Get schema by subject and version."""
        try:
            response = self.session.get(f"{self.schema_registry_url}/subjects/{subject}/versions/{version}")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Error getting schema {subject} v{version}: {e}")
        return None
    
    def check_compatibility(self, subject: str, version: int, schema: str) -> Dict:
        """Check compatibility of a schema with existing versions."""
        try:
            payload = {
                "schema": schema
            }
            response = self.session.post(
                f"{self.schema_registry_url}/compatibility/subjects/{subject}/versions/{version}",
                data=json.dumps(payload)
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Error checking compatibility for {subject}: {e}")
        return {"is_compatible": False, "error": "Check failed"}
    
    def validate_dependency_compatibility(self, dependency_name: str, dependency_version: str) -> Dict:
        """Validate compatibility of a Kafka-related dependency."""
        validation_result = {
            "dependency": dependency_name,
            "version": dependency_version,
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "compatible": True,
            "issues": [],
            "schema_subjects": [],
            "recommendations": []
        }
        
        try:
            # Get all subjects
            subjects = self.get_subjects()
            validation_result["schema_subjects"] = subjects
            
            # Check for Kafka-related dependencies
            kafka_related = ['kafka', 'schema', 'avro', 'confluent']
            if any(keyword in dependency_name.lower() for keyword in kafka_related):
                # Validate each subject
                for subject in subjects:
                    versions = self.get_schema_versions(subject)
                    for version in versions:
                        schema_info = self.get_schema_by_version(subject, version)
                        if schema_info:
                            # Check if schema has changed in a way that might affect compatibility
                            # This is a simplified check - in reality, you'd compare against
                            # the expected schema for this dependency version
                            schema_str = schema_info.get('schema', '{}')
                            
                            # Check compatibility with latest version
                            if versions and version == max(versions):
                                compatibility = self.check_compatibility(subject, "latest", schema_str)
                                if not compatibility.get("is_compatible", True):
                                    validation_result["compatible"] = False
                                    validation_result["issues"].append({
                                        "subject": subject,
                                        "version": version,
                                        "issue": "Schema compatibility issue detected",
                                        "details": compatibility.get("error", "Unknown compatibility issue")
                                    })
                                    validation_result["recommendations"].append(
                                        f"Review schema changes for {subject} before updating {dependency_name}"
                                    )
            
            # Special validation for Schema Registry itself
            if 'schema-registry' in dependency_name.lower():
                # Check if Schema Registry is responsive
                try:
                    response = self.session.get(f"{self.schema_registry_url}/config")
                    if response.status_code != 200:
                        validation_result["compatible"] = False
                        validation_result["issues"].append({
                            "issue": "Schema Registry not responsive",
                            "details": f"HTTP {response.status_code}"
                        })
                except Exception as e:
                    validation_result["compatible"] = False
                    validation_result["issues"].append({
                        "issue": "Schema Registry connection failed",
                        "details": str(e)
                    })
                    
        except Exception as e:
            validation_result["compatible"] = False
            validation_result["issues"].append({
                "issue": "Validation process failed",
                "details": str(e)
            })
            
        return validation_result
    
    def generate_compatibility_report(self, dependencies: List[Dict]) -> Dict:
        """Generate a comprehensive compatibility report."""
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "schema_registry_url": self.schema_registry_url,
            "total_dependencies": len(dependencies),
            "compatible_dependencies": 0,
            "incompatible_dependencies": 0,
            "validation_results": []
        }
        
        for dep in dependencies:
            name = dep.get('name', 'unknown')
            version = dep.get('version', 'unknown')
            
            result = self.validate_dependency_compatibility(name, version)
            report["validation_results"].append(result)
            
            if result["compatible"]:
                report["compatible_dependencies"] += 1
            else:
                report["incompatible_dependencies"] += 1
        
        return report

def load_dependencies_from_tiers() -> List[Dict]:
    """Load dependencies from tier configuration files."""
    dependencies = []
    tier_files = [
        'dependency_management/tiers/tier1_critical.json',
        'dependency_management/tiers/tier2_important.json',
        'dependency_management/tiers/tier3_supporting.json',
        'dependency_management/tiers/tier4_infrastructure.json'
    ]
    
    for tier_file in tier_files:
        try:
            if os.path.exists(tier_file):
                with open(tier_file, 'r') as f:
                    data = json.load(f)
                    for dep in data.get('dependencies', []):
                        # Add version information if available
                        dep_info = {
                            'name': dep.get('name', ''),
                            'repository': dep.get('repository', ''),
                            'version': 'latest',  # Default to latest
                            'type': dep.get('type', 'unknown'),
                            'tier': data.get('tier', 'unknown')
                        }
                        dependencies.append(dep_info)
        except Exception as e:
            logger.error(f"Error loading {tier_file}: {e}")
    
    return dependencies

def main():
    """Main function to validate Schema Registry compatibility."""
    print("Starting Schema Registry validation...")
    
    validator = SchemaRegistryValidator()
    
    # Load dependencies
    dependencies = load_dependencies_from_tiers()
    
    # Filter for Kafka-related dependencies
    kafka_dependencies = [
        dep for dep in dependencies 
        if any(keyword in dep['name'].lower() for keyword in ['kafka', 'schema', 'confluent'])
    ]
    
    if not kafka_dependencies:
        print("No Kafka-related dependencies found for validation.")
        return 0
    
    print(f"Validating {len(kafka_dependencies)} Kafka-related dependencies...")
    
    # Generate report
    report = validator.generate_compatibility_report(kafka_dependencies)
    
    # Output results
    print("\n=== SCHEMA REGISTRY COMPATIBILITY REPORT ===")
    print(f"Generated at: {report['generated_at']}")
    print(f"Schema Registry URL: {report['schema_registry_url']}")
    print(f"Total dependencies checked: {report['total_dependencies']}")
    print(f"Compatible: {report['compatible_dependencies']}")
    print(f"Incompatible: {report['incompatible_dependencies']}")
    
    # Show detailed results
    if report['incompatible_dependencies'] > 0:
        print("\nIncompatible Dependencies:")
        for result in report['validation_results']:
            if not result['compatible']:
                print(f"\n  {result['dependency']} ({result['version']})")
                for issue in result['issues']:
                    print(f"    - {issue['issue']}: {issue['details']}")
                if result['recommendations']:
                    print("    Recommendations:")
                    for rec in result['recommendations']:
                        print(f"      - {rec}")
    
    # Exit with error code if incompatible dependencies found
    if report['incompatible_dependencies'] > 0:
        print("\nINCOMPATIBLE DEPENDENCIES FOUND - ACTION REQUIRED")
        return 1
    else:
        print("\nAll dependencies are compatible with Schema Registry.")
        return 0

if __name__ == "__main__":
    sys.exit(main())