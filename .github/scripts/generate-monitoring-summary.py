#!/usr/bin/env python3
"""
Monitoring Summary Generator
Generates comprehensive monitoring summaries for all repository tiers
"""

import json
import os
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

class MonitoringSummaryGenerator:
    def __init__(self, tier: str, repository: str, run_id: str, failures_only: bool = False):
        self.tier = tier
        self.repository = repository
        self.run_id = run_id
        self.failures_only = failures_only
        self.timestamp = datetime.now(timezone.utc).isoformat()
        
        # Tier-specific configurations
        self.tier_config = {
            "1": {
                "name": "Critical",
                "priority": "HIGH",
                "alert_threshold": 0,  # Alert on any issue
                "components": ["security", "performance", "infrastructure", "compliance"]
            },
            "2": {
                "name": "Important", 
                "priority": "MEDIUM",
                "alert_threshold": 2,  # Alert on 2+ issues
                "components": ["security", "dependencies", "quality", "coverage"]
            },
            "3": {
                "name": "Standard",
                "priority": "LOW", 
                "alert_threshold": 5,  # Alert on 5+ issues
                "components": ["security", "dependencies", "build", "lint"]
            },
            "4": {
                "name": "Experimental",
                "priority": "MINIMAL",
                "alert_threshold": 10,  # Alert on 10+ critical issues
                "components": ["security", "dependencies", "build", "health"]
            }
        }
    
    def collect_reports(self) -> Dict[str, Any]:
        """Collect all available monitoring reports"""
        reports = {}
        
        # Look for artifact directories
        artifact_dirs = [d for d in Path('.').iterdir() if d.is_dir() and f'tier{self.tier}' in d.name]
        
        for artifact_dir in artifact_dirs:
            component = self._extract_component_name(artifact_dir.name)
            reports[component] = self._load_component_reports(artifact_dir)
        
        return reports
    
    def _extract_component_name(self, artifact_name: str) -> str:
        """Extract component name from artifact directory"""
        parts = artifact_name.split('-')
        if len(parts) >= 2:
            return parts[1]  # e.g., 'tier1-security-123' -> 'security'
        return 'unknown'
    
    def _load_component_reports(self, artifact_dir: Path) -> Dict[str, Any]:
        """Load all JSON reports from component directory"""
        component_data = {
            'status': 'unknown',
            'issues': [],
            'metrics': {},
            'files': []
        }
        
        for report_file in artifact_dir.glob('*.json'):
            try:
                with open(report_file, 'r') as f:
                    data = json.load(f)
                    component_data['files'].append(str(report_file))
                    
                    # Parse different report types
                    if 'bandit' in report_file.name:
                        component_data.update(self._parse_bandit_report(data))
                    elif 'safety' in report_file.name:
                        component_data.update(self._parse_safety_report(data))
                    elif 'coverage' in report_file.name:
                        component_data.update(self._parse_coverage_report(data))
                    elif 'summary' in report_file.name:
                        component_data.update(data)
                        
            except Exception as e:
                print(f"Warning: Could not parse {report_file}: {e}")
                component_data['issues'].append({
                    'type': 'parse_error',
                    'severity': 'medium',
                    'message': f"Failed to parse {report_file.name}: {str(e)}"
                })
        
        return component_data
    
    def _parse_bandit_report(self, data: Dict) -> Dict[str, Any]:
        """Parse Bandit security scan report"""
        issues = []
        
        if 'results' in data:
            for result in data['results']:
                issues.append({
                    'type': 'security',
                    'severity': result.get('issue_severity', 'unknown').lower(),
                    'message': result.get('issue_text', 'Security issue detected'),
                    'file': result.get('filename', 'unknown'),
                    'line': result.get('line_number', 0),
                    'test_id': result.get('test_id', 'unknown')
                })
        
        return {
            'status': 'failed' if issues else 'passed',
            'issues': issues,
            'metrics': {
                'total_issues': len(issues),
                'high_severity': len([i for i in issues if i['severity'] == 'high']),
                'medium_severity': len([i for i in issues if i['severity'] == 'medium']),
                'low_severity': len([i for i in issues if i['severity'] == 'low'])
            }
        }
    
    def _parse_safety_report(self, data: Dict) -> Dict[str, Any]:
        """Parse Safety vulnerability report"""
        issues = []
        
        if isinstance(data, list):
            for vuln in data:
                issues.append({
                    'type': 'vulnerability',
                    'severity': 'high',  # All safety issues are considered high
                    'message': vuln.get('advisory', 'Vulnerability detected'),
                    'package': vuln.get('package_name', 'unknown'),
                    'version': vuln.get('installed_version', 'unknown'),
                    'cve': vuln.get('vulnerability_id', 'unknown')
                })
        
        return {
            'status': 'failed' if issues else 'passed',
            'issues': issues,
            'metrics': {
                'total_vulnerabilities': len(issues),
                'affected_packages': len(set(i['package'] for i in issues))
            }
        }
    
    def _parse_coverage_report(self, data: Dict) -> Dict[str, Any]:
        """Parse test coverage report"""
        coverage_percent = data.get('totals', {}).get('percent_covered', 0)
        
        issues = []
        if coverage_percent < 80:  # Configurable threshold
            issues.append({
                'type': 'coverage',
                'severity': 'medium' if coverage_percent > 60 else 'high',
                'message': f"Test coverage is {coverage_percent:.1f}% (below 80% threshold)"
            })
        
        return {
            'status': 'passed' if coverage_percent >= 80 else 'warning',
            'issues': issues,
            'metrics': {
                'coverage_percent': coverage_percent,
                'lines_covered': data.get('totals', {}).get('covered_lines', 0),
                'lines_total': data.get('totals', {}).get('num_statements', 0)
            }
        }
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate comprehensive monitoring summary"""
        reports = self.collect_reports()
        
        # Calculate overall metrics
        total_issues = sum(len(report.get('issues', [])) for report in reports.values())
        critical_issues = sum(
            len([i for i in report.get('issues', []) if i.get('severity') == 'high'])
            for report in reports.values()
        )
        
        # Determine overall status
        config = self.tier_config[self.tier]
        if critical_issues > 0:
            overall_status = 'critical'
        elif total_issues > config['alert_threshold']:
            overall_status = 'warning'
        else:
            overall_status = 'healthy'
        
        # Filter reports if failures_only is True
        if self.failures_only:
            reports = {k: v for k, v in reports.items() 
                      if v.get('status') in ['failed', 'warning'] or v.get('issues')}
        
        summary = {
            'metadata': {
                'tier': self.tier,
                'tier_name': config['name'],
                'repository': self.repository,
                'run_id': self.run_id,
                'timestamp': self.timestamp,
                'priority': config['priority']
            },
            'overall': {
                'status': overall_status,
                'total_issues': total_issues,
                'critical_issues': critical_issues,
                'alert_threshold': config['alert_threshold'],
                'should_alert': total_issues > config['alert_threshold'] or critical_issues > 0
            },
            'components': reports,
            'recommendations': self._generate_recommendations(reports, overall_status)
        }
        
        return summary
    
    def _generate_recommendations(self, reports: Dict[str, Any], status: str) -> List[str]:
        """Generate actionable recommendations based on findings"""
        recommendations = []
        
        if status == 'critical':
            recommendations.append("🚨 CRITICAL: Immediate attention required")
        
        for component, report in reports.items():
            issues = report.get('issues', [])
            high_issues = [i for i in issues if i.get('severity') == 'high']
            
            if high_issues:
                recommendations.append(f"🔴 Fix {len(high_issues)} high-severity {component} issues")
            
            # Component-specific recommendations
            if component == 'security' and issues:
                recommendations.append("🔒 Review security scan results and update vulnerable dependencies")
            elif component == 'coverage' and report.get('metrics', {}).get('coverage_percent', 100) < 80:
                recommendations.append("📊 Increase test coverage to meet 80% threshold")
            elif component == 'dependencies' and issues:
                recommendations.append("📦 Update vulnerable packages to latest secure versions")
        
        if not recommendations:
            recommendations.append("✅ All checks passed - no immediate action required")
        
        return recommendations
    
    def save_summary(self, summary: Dict[str, Any]) -> None:
        """Save summary to JSON file"""
        with open('monitoring-summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"Generated monitoring summary for Tier {self.tier} ({self.tier_config[self.tier]['name']})")
        print(f"Overall Status: {summary['overall']['status'].upper()}")
        print(f"Total Issues: {summary['overall']['total_issues']}")
        print(f"Critical Issues: {summary['overall']['critical_issues']}")
        
        if summary['overall']['should_alert']:
            print("⚠️  Alert threshold exceeded - notifications will be sent")

def main():
    parser = argparse.ArgumentParser(description='Generate monitoring summary')
    parser.add_argument('--tier', required=True, choices=['1', '2', '3', '4'],
                       help='Repository tier (1=Critical, 2=Important, 3=Standard, 4=Experimental)')
    parser.add_argument('--repository', required=True, help='Repository name')
    parser.add_argument('--run-id', required=True, help='GitHub Actions run ID')
    parser.add_argument('--failures-only', action='store_true',
                       help='Only include components with failures or warnings')
    
    args = parser.parse_args()
    
    generator = MonitoringSummaryGenerator(
        tier=args.tier,
        repository=args.repository,
        run_id=args.run_id,
        failures_only=args.failures_only
    )
    
    summary = generator.generate_summary()
    generator.save_summary(summary)
    
    # Exit with appropriate code
    if summary['overall']['status'] == 'critical':
        sys.exit(2)
    elif summary['overall']['status'] == 'warning':
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()