#!/usr/bin/env python3
"""
Automated Security Scanner
Comprehensive SAST and vulnerability scanning for institutional-grade security
"""

import json
import os
import sys
import subprocess
import argparse
import yaml
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SecurityFinding:
    """Represents a security finding"""
    test_id: str
    severity: str
    confidence: str
    filename: str
    line_number: int
    issue_text: str
    code: str
    more_info: str
    
@dataclass
class VulnerabilityFinding:
    """Represents a vulnerability finding"""
    package_name: str
    installed_version: str
    vulnerability_id: str
    advisory: str
    severity: str

class SecurityScanner:
    def __init__(self, config_path: str = None, target_path: str = None):
        self.config_path = config_path or 'security/bandit_config.yaml'
        self.target_path = target_path or '.'
        self.config = self._load_config()
        self.results = {
            'metadata': {
                'scan_timestamp': datetime.now(timezone.utc).isoformat(),
                'scanner_version': '1.0.0',
                'target_path': os.path.abspath(self.target_path)
            },
            'security_findings': [],
            'vulnerability_findings': [],
            'compliance_status': {},
            'risk_assessment': {},
            'remediation_plan': []
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """Load security scanner configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {self.config_path} not found, using defaults")
            return self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'severity': {'level': 'medium'},
            'confidence': {'level': 'medium'},
            'format': 'json',
            'exclude_dirs': ['/tests/', '/.venv/', '/node_modules/'],
            'compliance': {
                'sox_requirements': ['No hardcoded credentials'],
                'pci_requirements': ['Strong cryptography'],
                'gdpr_requirements': ['Data encryption']
            }
        }
    
    def run_bandit_scan(self) -> Dict[str, Any]:
        """Run Bandit SAST scan"""
        logger.info("Starting Bandit SAST scan...")
        
        try:
            # Build Bandit command
            cmd = [
                'bandit',
                '-r', self.target_path,
                '-f', 'json',
                '-o', 'bandit-report.json'
            ]
            
            # Add configuration file if exists
            if os.path.exists(self.config_path):
                cmd.extend(['-c', self.config_path])
            
            # Add severity and confidence levels
            severity_level = self.config.get('severity', {}).get('level', 'medium')
            confidence_level = self.config.get('confidence', {}).get('level', 'medium')
            
            if severity_level == 'high':
                cmd.append('-ll')
            elif severity_level == 'medium':
                cmd.append('-l')
            
            # Add exclude directories
            exclude_dirs = self.config.get('exclude_dirs', [])
            for exclude_dir in exclude_dirs:
                cmd.extend(['--exclude', exclude_dir])
            
            # Run Bandit
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            # Load results
            if os.path.exists('bandit-report.json'):
                with open('bandit-report.json', 'r') as f:
                    bandit_data = json.load(f)
                
                # Parse findings
                findings = []
                for result_item in bandit_data.get('results', []):
                    finding = SecurityFinding(
                        test_id=result_item.get('test_id', ''),
                        severity=result_item.get('issue_severity', 'UNKNOWN'),
                        confidence=result_item.get('issue_confidence', 'UNKNOWN'),
                        filename=result_item.get('filename', ''),
                        line_number=result_item.get('line_number', 0),
                        issue_text=result_item.get('issue_text', ''),
                        code=result_item.get('code', ''),
                        more_info=result_item.get('more_info', '')
                    )
                    findings.append(finding)
                
                self.results['security_findings'] = findings
                logger.info(f"Bandit scan completed: {len(findings)} findings")
                return bandit_data
            else:
                logger.error("Bandit report file not generated")
                return {}
                
        except subprocess.TimeoutExpired:
            logger.error("Bandit scan timed out")
            return {}
        except Exception as e:
            logger.error(f"Bandit scan failed: {e}")
            return {}
    
    def run_safety_scan(self) -> Dict[str, Any]:
        """Run Safety vulnerability scan"""
        logger.info("Starting Safety vulnerability scan...")
        
        try:
            # Run Safety check
            cmd = ['safety', 'check', '--json', '--output', 'safety-report.json']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            # Load results
            if os.path.exists('safety-report.json'):
                with open('safety-report.json', 'r') as f:
                    safety_data = json.load(f)
                
                # Parse vulnerabilities
                vulnerabilities = []
                if isinstance(safety_data, list):
                    for vuln in safety_data:
                        vulnerability = VulnerabilityFinding(
                            package_name=vuln.get('package_name', ''),
                            installed_version=vuln.get('installed_version', ''),
                            vulnerability_id=vuln.get('vulnerability_id', ''),
                            advisory=vuln.get('advisory', ''),
                            severity='HIGH'  # Safety considers all findings high severity
                        )
                        vulnerabilities.append(vulnerability)
                
                self.results['vulnerability_findings'] = vulnerabilities
                logger.info(f"Safety scan completed: {len(vulnerabilities)} vulnerabilities")
                return safety_data
            else:
                logger.info("No vulnerabilities found by Safety")
                return []
                
        except subprocess.TimeoutExpired:
            logger.error("Safety scan timed out")
            return []
        except Exception as e:
            logger.error(f"Safety scan failed: {e}")
            return []
    
    def run_custom_patterns_scan(self) -> List[Dict[str, Any]]:
        """Run custom security pattern detection"""
        logger.info("Running custom security patterns scan...")
        
        custom_findings = []
        custom_rules = self.config.get('custom_rules', {})
        
        try:
            # Scan Python files for custom patterns
            for py_file in Path(self.target_path).rglob('*.py'):
                if any(exclude in str(py_file) for exclude in self.config.get('exclude_dirs', [])):
                    continue
                
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.split('\n')
                    
                    # Check each custom rule
                    for rule_name, rule_config in custom_rules.items():
                        pattern = rule_config.get('pattern', '')
                        if pattern:
                            import re
                            matches = re.finditer(pattern, content, re.IGNORECASE)
                            
                            for match in matches:
                                # Find line number
                                line_num = content[:match.start()].count('\n') + 1
                                
                                custom_findings.append({
                                    'rule_name': rule_name,
                                    'severity': rule_config.get('severity', 'MEDIUM'),
                                    'message': rule_config.get('message', 'Custom pattern detected'),
                                    'filename': str(py_file),
                                    'line_number': line_num,
                                    'matched_text': match.group(),
                                    'pattern': pattern
                                })
                
                except Exception as e:
                    logger.warning(f"Error scanning {py_file}: {e}")
            
            logger.info(f"Custom patterns scan completed: {len(custom_findings)} findings")
            return custom_findings
            
        except Exception as e:
            logger.error(f"Custom patterns scan failed: {e}")
            return []
    
    def assess_compliance(self) -> Dict[str, Any]:
        """Assess compliance with institutional standards"""
        logger.info("Assessing compliance status...")
        
        compliance_status = {
            'sox_compliance': {'status': 'PASS', 'issues': []},
            'pci_compliance': {'status': 'PASS', 'issues': []},
            'gdpr_compliance': {'status': 'PASS', 'issues': []},
            'overall_score': 0.0
        }
        
        # Check for hardcoded credentials (SOX requirement)
        credential_issues = [
            f for f in self.results['security_findings']
            if f.test_id in ['B105', 'B106', 'B107'] or 'password' in f.issue_text.lower()
        ]
        
        if credential_issues:
            compliance_status['sox_compliance']['status'] = 'FAIL'
            compliance_status['sox_compliance']['issues'] = [
                f"Hardcoded credentials found: {f.filename}:{f.line_number}"
                for f in credential_issues
            ]
        
        # Check for weak cryptography (PCI requirement)
        crypto_issues = [
            f for f in self.results['security_findings']
            if f.test_id in ['B303', 'B304', 'B305', 'B324', 'B505']
        ]
        
        if crypto_issues:
            compliance_status['pci_compliance']['status'] = 'FAIL'
            compliance_status['pci_compliance']['issues'] = [
                f"Weak cryptography found: {f.filename}:{f.line_number}"
                for f in crypto_issues
            ]
        
        # Check for data exposure (GDPR requirement)
        data_issues = [
            f for f in self.results['security_findings']
            if 'data' in f.issue_text.lower() or f.test_id in ['B608']
        ]
        
        if data_issues:
            compliance_status['gdpr_compliance']['status'] = 'FAIL'
            compliance_status['gdpr_compliance']['issues'] = [
                f"Data exposure risk: {f.filename}:{f.line_number}"
                for f in data_issues
            ]
        
        # Calculate overall compliance score
        passed_checks = sum(1 for check in compliance_status.values() 
                          if isinstance(check, dict) and check.get('status') == 'PASS')
        total_checks = 3  # SOX, PCI, GDPR
        compliance_status['overall_score'] = passed_checks / total_checks
        
        self.results['compliance_status'] = compliance_status
        return compliance_status
    
    def assess_risk(self) -> Dict[str, Any]:
        """Perform risk assessment"""
        logger.info("Performing risk assessment...")
        
        # Count findings by severity
        high_severity = len([f for f in self.results['security_findings'] if f.severity == 'HIGH'])
        medium_severity = len([f for f in self.results['security_findings'] if f.severity == 'MEDIUM'])
        low_severity = len([f for f in self.results['security_findings'] if f.severity == 'LOW'])
        
        # Count vulnerabilities
        vulnerabilities = len(self.results['vulnerability_findings'])
        
        # Calculate risk score (0-100)
        risk_score = min(100, (
            high_severity * 20 +
            medium_severity * 10 +
            low_severity * 5 +
            vulnerabilities * 15
        ))
        
        # Determine risk level
        if risk_score >= 80:
            risk_level = 'CRITICAL'
        elif risk_score >= 60:
            risk_level = 'HIGH'
        elif risk_score >= 40:
            risk_level = 'MEDIUM'
        elif risk_score >= 20:
            risk_level = 'LOW'
        else:
            risk_level = 'MINIMAL'
        
        risk_assessment = {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'findings_summary': {
                'high_severity': high_severity,
                'medium_severity': medium_severity,
                'low_severity': low_severity,
                'vulnerabilities': vulnerabilities
            },
            'risk_factors': [],
            'mitigation_priority': []
        }
        
        # Identify key risk factors
        if high_severity > 0:
            risk_assessment['risk_factors'].append(f"{high_severity} high-severity security issues")
            risk_assessment['mitigation_priority'].append("Address high-severity security findings immediately")
        
        if vulnerabilities > 0:
            risk_assessment['risk_factors'].append(f"{vulnerabilities} known vulnerabilities in dependencies")
            risk_assessment['mitigation_priority'].append("Update vulnerable dependencies")
        
        if self.results['compliance_status']['overall_score'] < 1.0:
            risk_assessment['risk_factors'].append("Compliance violations detected")
            risk_assessment['mitigation_priority'].append("Address compliance violations")
        
        self.results['risk_assessment'] = risk_assessment
        return risk_assessment
    
    def generate_remediation_plan(self) -> List[Dict[str, Any]]:
        """Generate actionable remediation plan"""
        logger.info("Generating remediation plan...")
        
        remediation_plan = []
        
        # Group findings by type and priority
        high_priority_findings = [f for f in self.results['security_findings'] if f.severity == 'HIGH']
        vulnerabilities = self.results['vulnerability_findings']
        
        # High-priority security fixes
        for finding in high_priority_findings:
            remediation_plan.append({
                'priority': 'CRITICAL',
                'category': 'Security',
                'title': f"Fix {finding.test_id}: {finding.issue_text}",
                'description': f"Address security issue in {finding.filename}:{finding.line_number}",
                'file': finding.filename,
                'line': finding.line_number,
                'remediation_steps': self._get_remediation_steps(finding.test_id),
                'estimated_effort': 'Medium',
                'compliance_impact': 'High'
            })
        
        # Vulnerability fixes
        for vuln in vulnerabilities:
            remediation_plan.append({
                'priority': 'HIGH',
                'category': 'Dependency',
                'title': f"Update {vuln.package_name} to fix {vuln.vulnerability_id}",
                'description': vuln.advisory,
                'package': vuln.package_name,
                'current_version': vuln.installed_version,
                'remediation_steps': [
                    f"Update {vuln.package_name} to latest secure version",
                    "Test application functionality after update",
                    "Verify vulnerability is resolved"
                ],
                'estimated_effort': 'Low',
                'compliance_impact': 'Medium'
            })
        
        # Compliance fixes
        compliance_status = self.results['compliance_status']
        for standard, status in compliance_status.items():
            if isinstance(status, dict) and status.get('status') == 'FAIL':
                for issue in status.get('issues', []):
                    remediation_plan.append({
                        'priority': 'HIGH',
                        'category': 'Compliance',
                        'title': f"Fix {standard.upper()} compliance issue",
                        'description': issue,
                        'remediation_steps': self._get_compliance_remediation(standard),
                        'estimated_effort': 'Medium',
                        'compliance_impact': 'Critical'
                    })
        
        # Sort by priority
        priority_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        remediation_plan.sort(key=lambda x: priority_order.get(x['priority'], 4))
        
        self.results['remediation_plan'] = remediation_plan
        return remediation_plan
    
    def _get_remediation_steps(self, test_id: str) -> List[str]:
        """Get specific remediation steps for Bandit test ID"""
        remediation_map = {
            'B105': ['Remove hardcoded password', 'Use environment variables or secure vault'],
            'B106': ['Remove hardcoded password from function argument', 'Use secure parameter passing'],
            'B107': ['Remove hardcoded password default', 'Use configuration management'],
            'B301': ['Replace pickle with safer serialization', 'Use JSON or secure alternatives'],
            'B303': ['Replace MD5 with SHA-256 or stronger', 'Use cryptographically secure hashing'],
            'B311': ['Replace random with secrets module', 'Use cryptographically secure random'],
            'B501': ['Enable SSL certificate validation', 'Use proper SSL context'],
            'B608': ['Use parameterized queries', 'Implement proper SQL injection protection']
        }
        
        return remediation_map.get(test_id, ['Review security documentation', 'Implement secure coding practices'])
    
    def _get_compliance_remediation(self, standard: str) -> List[str]:
        """Get compliance-specific remediation steps"""
        remediation_map = {
            'sox_compliance': [
                'Implement secure credential management',
                'Use environment variables for sensitive data',
                'Implement audit logging',
                'Review access controls'
            ],
            'pci_compliance': [
                'Implement strong encryption',
                'Use secure communication protocols',
                'Implement proper key management',
                'Regular security testing'
            ],
            'gdpr_compliance': [
                'Implement data encryption',
                'Review data processing procedures',
                'Implement privacy by design',
                'Document data handling processes'
            ]
        }
        
        return remediation_map.get(standard, ['Review compliance requirements', 'Implement necessary controls'])
    
    def send_alerts(self) -> None:
        """Send security alerts based on findings"""
        risk_level = self.results['risk_assessment']['risk_level']
        
        if risk_level in ['CRITICAL', 'HIGH']:
            logger.info(f"Sending {risk_level} security alert...")
            
            # Prepare alert data
            alert_data = {
                'timestamp': self.results['metadata']['scan_timestamp'],
                'risk_level': risk_level,
                'risk_score': self.results['risk_assessment']['risk_score'],
                'findings_count': len(self.results['security_findings']),
                'vulnerabilities_count': len(self.results['vulnerability_findings']),
                'compliance_score': self.results['compliance_status']['overall_score'],
                'target_path': self.results['metadata']['target_path']
            }
            
            # Send to configured webhooks
            self._send_webhook_alert(alert_data)
    
    def _send_webhook_alert(self, alert_data: Dict[str, Any]) -> None:
        """Send alert to configured webhooks"""
        webhooks = {
            'teams': os.getenv('TEAMS_SECURITY_WEBHOOK'),
            'discord': os.getenv('DISCORD_SECURITY_WEBHOOK')
        }
        
        for platform, webhook_url in webhooks.items():
            if webhook_url:
                try:
                    if platform == 'teams':
                        payload = self._format_teams_alert(alert_data)
                    elif platform == 'discord':
                        payload = self._format_discord_alert(alert_data)
                    
                    response = requests.post(webhook_url, json=payload, timeout=30)
                    response.raise_for_status()
                    logger.info(f"Alert sent to {platform}")
                    
                except Exception as e:
                    logger.error(f"Failed to send alert to {platform}: {e}")
    
    def _format_teams_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format alert for Microsoft Teams"""
        color = "FF0000" if alert_data['risk_level'] == 'CRITICAL' else "FFA500"
        
        return {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": f"Security Alert: {alert_data['risk_level']}",
            "themeColor": color,
            "sections": [{
                "activityTitle": f"🚨 {alert_data['risk_level']} Security Alert",
                "facts": [
                    {"name": "Risk Score", "value": str(alert_data['risk_score'])},
                    {"name": "Security Findings", "value": str(alert_data['findings_count'])},
                    {"name": "Vulnerabilities", "value": str(alert_data['vulnerabilities_count'])},
                    {"name": "Compliance Score", "value": f"{alert_data['compliance_score']:.2%}"}
                ]
            }]
        }
    
    def _format_discord_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format alert for Discord"""
        color = 0xFF0000 if alert_data['risk_level'] == 'CRITICAL' else 0xFFA500
        
        return {
            "embeds": [{
                "title": f"🚨 {alert_data['risk_level']} Security Alert",
                "color": color,
                "fields": [
                    {"name": "Risk Score", "value": str(alert_data['risk_score']), "inline": True},
                    {"name": "Security Findings", "value": str(alert_data['findings_count']), "inline": True},
                    {"name": "Vulnerabilities", "value": str(alert_data['vulnerabilities_count']), "inline": True}
                ],
                "timestamp": alert_data['timestamp']
            }]
        }
    
    def save_results(self, output_file: str = 'security-scan-results.json') -> None:
        """Save scan results to file"""
        with open(output_file, 'w') as f:
            # Convert dataclass objects to dictionaries for JSON serialization
            results_copy = self.results.copy()
            results_copy['security_findings'] = [
                {
                    'test_id': f.test_id,
                    'severity': f.severity,
                    'confidence': f.confidence,
                    'filename': f.filename,
                    'line_number': f.line_number,
                    'issue_text': f.issue_text,
                    'code': f.code,
                    'more_info': f.more_info
                } for f in self.results['security_findings']
            ]
            results_copy['vulnerability_findings'] = [
                {
                    'package_name': v.package_name,
                    'installed_version': v.installed_version,
                    'vulnerability_id': v.vulnerability_id,
                    'advisory': v.advisory,
                    'severity': v.severity
                } for v in self.results['vulnerability_findings']
            ]
            
            json.dump(results_copy, f, indent=2)
        
        logger.info(f"Results saved to {output_file}")
    
    def run_full_scan(self) -> Dict[str, Any]:
        """Run complete security scan"""
        logger.info("Starting comprehensive security scan...")
        
        # Run all scans
        self.run_bandit_scan()
        self.run_safety_scan()
        custom_findings = self.run_custom_patterns_scan()
        
        # Add custom findings to results
        self.results['custom_findings'] = custom_findings
        
        # Perform assessments
        self.assess_compliance()
        self.assess_risk()
        self.generate_remediation_plan()
        
        # Send alerts if necessary
        self.send_alerts()
        
        # Save results
        self.save_results()
        
        logger.info("Security scan completed")
        return self.results

def main():
    parser = argparse.ArgumentParser(description='Automated Security Scanner')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--target', default='.', help='Target directory to scan')
    parser.add_argument('--output', default='security-scan-results.json', help='Output file')
    parser.add_argument('--quiet', action='store_true', help='Suppress output')
    
    args = parser.parse_args()
    
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    # Run security scan
    scanner = SecurityScanner(config_path=args.config, target_path=args.target)
    results = scanner.run_full_scan()
    
    # Print summary
    if not args.quiet:
        print("\n" + "="*60)
        print("SECURITY SCAN SUMMARY")
        print("="*60)
        print(f"Risk Level: {results['risk_assessment']['risk_level']}")
        print(f"Risk Score: {results['risk_assessment']['risk_score']}/100")
        print(f"Security Findings: {len(results['security_findings'])}")
        print(f"Vulnerabilities: {len(results['vulnerability_findings'])}")
        print(f"Compliance Score: {results['compliance_status']['overall_score']:.2%}")
        print(f"Remediation Items: {len(results['remediation_plan'])}")
        print("="*60)
    
    # Exit with appropriate code
    risk_level = results['risk_assessment']['risk_level']
    if risk_level == 'CRITICAL':
        sys.exit(2)
    elif risk_level in ['HIGH', 'MEDIUM']:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()