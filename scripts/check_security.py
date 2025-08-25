#!/usr/bin/env python3

import argparse
import json
import requests
import os
from datetime import datetime
from pathlib import Path

class SecurityScanner:
    def __init__(self, github_token):
        self.github_token = github_token
        self.headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }

    def check_github_security_alerts(self, owner, repo):
        """Check GitHub security alerts and advisories"""
        alerts_url = f'https://api.github.com/repos/{owner}/{repo}/security/alerts'
        try:
            response = requests.get(alerts_url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {'error': str(e)}

    def check_dependency_vulnerabilities(self, dependency):
        """Check a dependency for known vulnerabilities"""
        if 'repository' not in dependency:
            return {'error': 'No repository URL provided'}

        # Extract owner/repo from URL
        try:
            parts = dependency['repository'].rstrip('/').split('/')
            owner, repo = parts[-2], parts[-1]
        except:
            return {'error': 'Invalid repository URL format'}

        # Get security alerts
        alerts = self.check_github_security_alerts(owner, repo)
        
        # Check PyPI safety database for Python packages
        pypi_vulns = self.check_pypi_vulnerabilities(dependency['name'], dependency.get('version', '0.0.0'))

        return {
            'github_alerts': alerts,
            'pypi_vulnerabilities': pypi_vulns,
            'last_checked': datetime.now().isoformat()
        }

    def check_pypi_vulnerabilities(self, package_name, version):
        """Check PyPI package for known vulnerabilities"""
        safety_db_url = "https://raw.githubusercontent.com/pyupio/safety-db/master/data/insecure_full.json"
        try:
            response = requests.get(safety_db_url)
            response.raise_for_status()
            safety_db = response.json()
            
            vulnerabilities = []
            if package_name in safety_db:
                for vuln in safety_db[package_name]:
                    if self._version_in_range(version, vuln.get('v')):
                        vulnerabilities.append({
                            'advisory': vuln.get('advisory'),
                            'spec': vuln.get('v'),
                            'cve': vuln.get('cve')
                        })
            return vulnerabilities
        except Exception as e:
            return {'error': str(e)}

    def _version_in_range(self, version, spec):
        """Check if version is in the vulnerable range"""
        # Implement version range checking logic
        # For now, return True if exact match
        return version in (spec if isinstance(spec, list) else [spec])

def scan_dependencies(tier, token):
    """Scan dependencies for security vulnerabilities"""
    scanner = SecurityScanner(token)
    results = []

    try:
        with open('dependency_management/dependencies.json', 'r') as f:
            deps_config = json.load(f)
        
        tier_deps = deps_config.get(f'tier{tier}', {}).get('dependencies', [])
        
        for dep in tier_deps:
            result = {
                'name': dep['name'],
                'version': dep.get('version', 'unknown'),
                'status': 'checking'
            }
            
            # Scan for vulnerabilities
            scan_result = scanner.check_dependency_vulnerabilities(dep)
            
            # Determine security status
            if 'error' in scan_result:
                result['status'] = 'error'
                result['error'] = scan_result['error']
            else:
                github_alerts = scan_result['github_alerts']
                pypi_vulns = scan_result['pypi_vulnerabilities']
                
                if isinstance(github_alerts, list) and isinstance(pypi_vulns, list):
                    critical_count = sum(1 for alert in github_alerts if alert.get('severity') == 'critical')
                    high_count = sum(1 for alert in github_alerts if alert.get('severity') == 'high')
                    
                    if critical_count > 0:
                        result['status'] = 'red'
                    elif high_count > 0 or pypi_vulns:
                        result['status'] = 'yellow'
                    else:
                        result['status'] = 'green'
                    
                    result['vulnerabilities'] = {
                        'github': {
                            'critical': critical_count,
                            'high': high_count,
                            'alerts': github_alerts
                        },
                        'pypi': pypi_vulns
                    }
                else:
                    result['status'] = 'error'
                    result['error'] = 'Failed to fetch security data'
            
            results.append(result)
    except Exception as e:
        print(f"Error scanning dependencies: {e}")
        return []

    # Save results
    try:
        output_file = 'security_status.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Security scan results saved to {output_file}")
    except Exception as e:
        print(f"Error saving results: {e}")

    return results

def main():
    parser = argparse.ArgumentParser(description='Scan dependencies for security vulnerabilities')
    parser.add_argument('--tier', type=int, required=True, help='Dependency tier to check')
    parser.add_argument('--token', type=str, required=True, help='GitHub token for API access')
    
    args = parser.parse_args()
    scan_dependencies(args.tier, args.token)

if __name__ == '__main__':
    main()
