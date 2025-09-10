#!/usr/bin/env python3
"""
Enhanced Dependency Monitoring System
Provides tiered monitoring with vulnerability scanning, Schema Registry integration,
and impact assessment for the Algorithmic Trading System.
"""

import json
import requests
import subprocess
import sys
import os
import argparse
from packaging import version
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedDependencyMonitor:
    def __init__(self, github_token: str = None):
        self.github_token = github_token or os.getenv('GITHUB_TOKEN')
        self.headers = {'Authorization': f'Bearer {self.github_token}'} if self.github_token else {}
        self.cve_database_url = "https://cve.circl.lu/api/search/"
        self.nvd_api_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
        
    def load_tier_dependencies(self, tier_file: str) -> List[Dict]:
        """Load dependencies from a tier JSON file."""
        try:
            with open(tier_file, 'r') as f:
                data = json.load(f)
            return data.get('dependencies', [])
        except Exception as e:
            logger.error(f"Error loading {tier_file}: {e}")
            return []
    
    def check_pypi_version(self, package_name: str) -> Optional[str]:
        """Check the latest version of a package on PyPI."""
        try:
            response = requests.get(f'https://pypi.org/pypi/{package_name}/json', timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data['info']['version']
        except Exception as e:
            logger.error(f"Error checking PyPI for {package_name}: {e}")
        return None
    
    def check_npm_version(self, package_name: str) -> Optional[str]:
        """Check the latest version of a package on npm."""
        try:
            response = requests.get(f'https://registry.npmjs.org/{package_name}', timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data['dist-tags']['latest']
        except Exception as e:
            logger.error(f"Error checking npm for {package_name}: {e}")
        return None
    
    def get_local_python_version(self, package_name: str) -> Optional[str]:
        """Get the locally installed version of a Python package."""
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'show', package_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('Version:'):
                        return line.split(':', 1)[1].strip()
        except Exception as e:
            logger.error(f"Error getting local version for {package_name}: {e}")
        return None
    
    def get_local_npm_version(self, package_name: str) -> Optional[str]:
        """Get the locally installed version of an npm package."""
        try:
            result = subprocess.run(
                ['npm', 'list', package_name, 'version'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if package_name in line and '@' in line:
                        return line.split('@')[-1]
        except Exception as e:
            logger.error(f"Error getting local npm version for {package_name}: {e}")
        return None
    
    def check_github_releases(self, repo_url: str) -> Optional[Dict]:
        """Check for latest releases on GitHub."""
        try:
            # Extract owner/repo from URL
            if 'github.com' in repo_url:
                parts = repo_url.rstrip('/').split('/')
                owner, repo = parts[-2], parts[-1]
                
                # Remove .git suffix if present
                if repo.endswith('.git'):
                    repo = repo[:-4]
                
                url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
                response = requests.get(url, headers=self.headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'tag_name': data.get('tag_name'),
                        'published_at': data.get('published_at'),
                        'body': data.get('body', '')[:500],  # First 500 chars
                        'html_url': data.get('html_url')
                    }
        except Exception as e:
            logger.error(f"Error checking GitHub releases for {repo_url}: {e}")
        return None
    
    def check_cve_vulnerabilities(self, package_name: str, version: str = None) -> List[Dict]:
        """Check for CVE vulnerabilities for a package."""
        vulnerabilities = []
        try:
            # Using circl.lu CVE search API
            search_term = package_name
            if version:
                search_term += f" {version}"
            
            response = requests.get(f"{self.cve_database_url}{search_term}", timeout=15)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    for item in data[:5]:  # Limit to first 5 results
                        if isinstance(item, dict) and 'cvss' in item:
                            vulnerabilities.append({
                                'id': item.get('id', 'Unknown'),
                                'cvss_score': item.get('cvss', 0),
                                'summary': item.get('summary', 'No summary available')[:200],
                                'published': item.get('Published', 'Unknown')
                            })
        except Exception as e:
            logger.error(f"Error checking CVE for {package_name}: {e}")
        return vulnerabilities
    
    def check_schema_registry_compatibility(self, dependency: Dict) -> Dict:
        """Check Schema Registry compatibility for Kafka-related dependencies."""
        compatibility_result = {
            'compatible': True,
            'issues': [],
            'schema_version': None
        }
        
        try:
            # This would connect to actual Schema Registry in production
            # For now, we'll simulate the check
            if 'kafka' in dependency.get('name', '').lower() or 'schema' in dependency.get('name', '').lower():
                # Simulate schema registry check
                compatibility_result['schema_version'] = "1.0.0"
                compatibility_result['compatible'] = True
        except Exception as e:
            compatibility_result['compatible'] = False
            compatibility_result['issues'].append(f"Schema Registry check failed: {e}")
            
        return compatibility_result
    
    def assess_impact(self, dependency: Dict, local_version: str, latest_version: str) -> Dict:
        """Assess the impact of updating a dependency."""
        impact_assessment = {
            'breaking_changes': False,
            'performance_impact': 'unknown',
            'compatibility_risk': 'low',
            'migration_required': False,
            'estimated_effort': 'low'
        }
        
        try:
            # Check changelog for breaking changes
            repo_info = self.check_github_releases(dependency.get('repository', ''))
            if repo_info and 'breaking' in repo_info.get('body', '').lower():
                impact_assessment['breaking_changes'] = True
                impact_assessment['compatibility_risk'] = 'high'
                impact_assessment['migration_required'] = True
                impact_assessment['estimated_effort'] = 'high'
            
            # Special handling for critical trading components
            critical_components = ['nautilus', 'kafka', 'langchain', 'fastapi']
            if any(comp in dependency.get('name', '').lower() for comp in critical_components):
                impact_assessment['performance_impact'] = 'high'
                if version.parse(latest_version) > version.parse(local_version):
                    # Check if major version bump (likely breaking changes)
                    local_major = version.parse(local_version).major
                    latest_major = version.parse(latest_version).major
                    if latest_major > local_major:
                        impact_assessment['breaking_changes'] = True
                        impact_assessment['compatibility_risk'] = 'high'
                        impact_assessment['migration_required'] = True
                        impact_assessment['estimated_effort'] = 'high'
        except Exception as e:
            logger.error(f"Error assessing impact for {dependency.get('name')}: {e}")
            
        return impact_assessment
    
    def generate_migration_path(self, dependency: Dict, local_version: str, latest_version: str) -> Dict:
        """Generate migration path for breaking changes."""
        migration_path = {
            'required': False,
            'steps': [],
            'estimated_time': '0h',
            'affected_services': []
        }
        
        try:
            # Check if major version change
            local_major = version.parse(local_version).major if local_version else 0
            latest_major = version.parse(latest_version).major if latest_version else 0
            
            if latest_major > local_major:
                migration_path['required'] = True
                migration_path['steps'] = [
                    "Review changelog for breaking changes",
                    "Update dependency in requirements.txt",
                    "Run unit tests",
                    "Run integration tests",
                    "Deploy to staging environment",
                    "Perform regression testing",
                    "Deploy to production"
                ]
                migration_path['estimated_time'] = "4h"  # Default estimate
                migration_path['affected_services'] = self.get_affected_services(dependency)
        except Exception as e:
            logger.error(f"Error generating migration path for {dependency.get('name')}: {e}")
            
        return migration_path
    
    def get_affected_services(self, dependency: Dict) -> List[str]:
        """Get list of services affected by a dependency update."""
        # This would be more sophisticated in a real implementation
        service_mapping = {
            'nautilus': ['trading_engine', 'backtesting_service'],
            'kafka': ['event_bus', 'market_data_service', 'order_processor'],
            'langchain': ['ai_assistant', 'trading_agents'],
            'fastapi': ['api_gateway', 'trading_api'],
            'redis': ['cache_service', 'session_manager'],
            'postgres': ['database_service', 'user_service'],
            'clickhouse': ['analytics_service', 'reporting_service']
        }
        
        dep_name = dependency.get('name', '').lower()
        for key, services in service_mapping.items():
            if key in dep_name:
                return services
        return ['unknown_service']
    
    def check_dependency_updates(self, dependencies: List[Dict], tier: str) -> List[Dict]:
        """Check for updates in dependencies with enhanced analysis."""
        updates_needed = []
        
        for dep in dependencies:
            name = dep['name']
            dep_type = dep['type']
            
            try:
                local_version = None
                latest_version = None
                
                if dep_type in ['trading_engine', 'event_bus', 'ai_framework', 'technical_analysis', 
                               'backtesting', 'reinforcement_learning', 'anomaly_detection',
                               'portfolio_optimization', 'risk_management', 'forecasting',
                               'quantitative_finance', 'nlp', 'deep_learning', 'explainable_ai',
                               'document_processing', 'vector_database', 'database',
                               'monitoring', 'distributed_tracing', 'log_aggregation',
                               'feature_flags', 'data_lake', 'security_scanning']:
                    
                    # Python package
                    local_version = self.get_local_python_version(name)
                    if local_version:
                        latest_version = self.check_pypi_version(name)
                        
                elif dep_type in ['no_code', 'visualization']:
                    # npm package
                    local_version = self.get_local_npm_version(name)
                    if local_version:
                        latest_version = self.check_npm_version(name)
                
                # Check for updates
                if local_version and latest_version:
                    if version.parse(latest_version) > version.parse(local_version):
                        # Check for vulnerabilities
                        vulnerabilities = self.check_cve_vulnerabilities(name, local_version)
                        
                        # Check Schema Registry compatibility
                        schema_compatibility = self.check_schema_registry_compatibility(dep)
                        
                        # Assess impact
                        impact = self.assess_impact(dep, local_version, latest_version)
                        
                        # Generate migration path if needed
                        migration_path = self.generate_migration_path(dep, local_version, latest_version)
                        
                        # Determine severity
                        severity = 'low'
                        if vulnerabilities:
                            max_cvss = max([v.get('cvss_score', 0) for v in vulnerabilities], default=0)
                            if max_cvss >= 9.0:
                                severity = 'critical'
                            elif max_cvss >= 7.0:
                                severity = 'high'
                            elif max_cvss >= 4.0:
                                severity = 'medium'
                        
                        if impact.get('breaking_changes') or impact.get('compatibility_risk') == 'high':
                            severity = max(severity, 'high')
                        
                        updates_needed.append({
                            'name': name,
                            'type': dep_type,
                            'tier': tier,
                            'local_version': local_version,
                            'latest_version': latest_version,
                            'vulnerabilities': vulnerabilities,
                            'schema_compatible': schema_compatibility,
                            'impact': impact,
                            'migration_path': migration_path,
                            'severity': severity,
                            'repository': dep.get('repository', ''),
                            'customizations': dep.get('customizations', [])
                        })
                        
            except Exception as e:
                logger.error(f"Error checking {name}: {e}")
                
        return updates_needed
    
    def generate_report(self, all_updates: List[Dict]) -> Dict:
        """Generate a comprehensive dependency monitoring report."""
        report = {
            'generated_at': datetime.now().isoformat(),
            'total_updates': len(all_updates),
            'critical_updates': len([u for u in all_updates if u.get('severity') == 'critical']),
            'high_updates': len([u for u in all_updates if u.get('severity') == 'high']),
            'medium_updates': len([u for u in all_updates if u.get('severity') == 'medium']),
            'low_updates': len([u for u in all_updates if u.get('severity') == 'low']),
            'updates_by_tier': {},
            'updates_by_severity': {},
            'updates_with_vulnerabilities': len([u for u in all_updates if u.get('vulnerabilities')]),
            'breaking_changes_count': len([u for u in all_updates if u.get('impact', {}).get('breaking_changes')]),
            'updates': all_updates
        }
        
        # Group by tier
        for update in all_updates:
            tier = update.get('tier', 'unknown')
            if tier not in report['updates_by_tier']:
                report['updates_by_tier'][tier] = 0
            report['updates_by_tier'][tier] += 1
            
            severity = update.get('severity', 'unknown')
            if severity not in report['updates_by_severity']:
                report['updates_by_severity'][severity] = 0
            report['updates_by_severity'][severity] += 1
            
        return report

def main():
    """Main function to check all tier dependencies."""
    parser = argparse.ArgumentParser(description='Enhanced Dependency Monitoring')
    parser.add_argument('--tier', help='Specific tier to monitor (tier1, tier2, tier3, tier4)')
    parser.add_argument('--output', help='Output file for report (JSON format)')
    args = parser.parse_args()
    
    print("Starting enhanced dependency monitoring...")
    
    monitor = EnhancedDependencyMonitor()
    
    # Define tier files
    tier_files = {
        'tier1': 'dependency_management/tiers/tier1_critical.json',
        'tier2': 'dependency_management/tiers/tier2_important.json',
        'tier3': 'dependency_management/tiers/tier3_supporting.json',
        'tier4': 'dependency_management/tiers/tier4_infrastructure.json'
    }
    
    # Filter by specific tier if provided
    if args.tier:
        if args.tier in tier_files:
            tier_files = {args.tier: tier_files[args.tier]}
        else:
            print(f"Unknown tier: {args.tier}")
            return 1
    
    all_updates = []
    
    # Check each tier
    for tier, tier_file in tier_files.items():
        if Path(tier_file).exists():
            print(f"Checking {tier_file}...")
            dependencies = monitor.load_tier_dependencies(tier_file)
            updates = monitor.check_dependency_updates(dependencies, tier)
            all_updates.extend(updates)
            print(f"Found {len(updates)} updates for {tier}")
        else:
            print(f"Warning: {tier_file} not found")
    
    # Generate report
    report = monitor.generate_report(all_updates)
    
    # Output report
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Report saved to {args.output}")
    else:
        print("\n=== ENHANCED DEPENDENCY MONITORING REPORT ===")
        print(f"Generated at: {report['generated_at']}")
        print(f"Total updates available: {report['total_updates']}")
        print(f"Critical: {report['critical_updates']}, High: {report['high_updates']}")
        print(f"Medium: {report['medium_updates']}, Low: {report['low_updates']}")
        print(f"Updates with vulnerabilities: {report['updates_with_vulnerabilities']}")
        print(f"Breaking changes: {report['breaking_changes_count']}")
        
        if all_updates:
            print("\nDetailed Updates:")
            for update in all_updates:
                print(f"\n  {update['name']} ({update['tier']}): {update['local_version']} -> {update['latest_version']}")
                print(f"    Severity: {update['severity']}")
                print(f"    Type: {update['type']}")
                if update.get('vulnerabilities'):
                    print(f"    Vulnerabilities: {len(update['vulnerabilities'])}")
                    for vuln in update['vulnerabilities'][:2]:  # Show first 2
                        print(f"      - {vuln['id']}: CVSS {vuln['cvss_score']}")
                if update.get('impact', {}).get('breaking_changes'):
                    print(f"    BREAKING CHANGES DETECTED")
                if update.get('migration_path', {}).get('required'):
                    print(f"    Migration required: {update['migration_path']['estimated_time']}")
    
    # Exit with error code if critical updates found
    if report['critical_updates'] > 0:
        print("\nCRITICAL UPDATES FOUND - IMMEDIATE ACTION REQUIRED")
        return 1
    elif report['high_updates'] > 0:
        print("\nHIGH PRIORITY UPDATES FOUND - ACTION RECOMMENDED")
        return 1
    elif all_updates:
        print("\nUPDATES AVAILABLE - REVIEW RECOMMENDED")
        return 0
    else:
        print("\nAll dependencies are up to date.")
        return 0

if __name__ == "__main__":
    sys.exit(main())