"""
Security Scanning Service for Dependency Management System

Provides comprehensive security scanning including:
- Static Application Security Testing (SAST) with Bandit
- CVE database integration and monitoring
- Dependency vulnerability scanning
- Security report generation

Author: Vincent S. Pereira
Version: 1.1.0
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import time
from monitoring.monitoring_infrastructure import monitoring
import aiohttp
from pydantic import BaseModel
from bandit.core import manager as bandit_manager
from bandit.core import config as b_config
import subprocess
import nvdlib
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Vulnerability(BaseModel):
    """Model for vulnerability data"""
    cve_id: str
    description: str
    severity: str
    cvss_score: float
    affected_versions: List[str]
    fix_versions: Optional[List[str]]
    references: List[str]
    discovered_date: datetime

class SecurityScan(BaseModel):
    """Model for security scan results"""
    dependency_name: str
    version: str
    vulnerabilities: List[Vulnerability]
    sast_findings: List[Dict]
    risk_score: float
    scan_date: datetime

class SecurityService:
    """Handles security scanning and vulnerability management"""
    
    def __init__(self):
        self.nvd_api_key = os.getenv("NVD_API_KEY")
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    async def scan_dependency(self, name: str, version: str, repo_info: Dict) -> SecurityScan:
        """Perform comprehensive security scan of a dependency"""
        tier = repo_info.get("tier", "unknown")
        scan_start = time.time()
        
        # Get repository path
        repo_path = self._get_repo_path(repo_info)
        if not repo_path:
            logger.warning(f"No valid repository path found for {name}")
            monitoring.log_error(tier, name, ValueError("Repository path not found"))
            # Still do vulnerability check even if no local repo to scan
            try:
                vuln_results = await self._check_vulnerabilities(name, version)
                risk_score = self._calculate_risk_score(vuln_results, [])
                
                scan_duration = time.time() - scan_start
                monitoring.record_scan_duration(tier, name, "vulnerability", scan_duration)
                
                return SecurityScan(
                    dependency_name=name,
                    version=version,
                    vulnerabilities=vuln_results,
                    sast_findings=[],
                    risk_score=risk_score,
                    scan_date=datetime.utcnow()
                )
            except Exception as e:
                monitoring.log_error(tier, name, e)
                raise
            
            try:
                tasks = [
                    self._check_vulnerabilities(name, version),
                    self._run_sast_scan(repo_path)
                ]
                
                vuln_results, sast_results = await asyncio.gather(*tasks)
                risk_score = self._calculate_risk_score(vuln_results, sast_results)
                
                # Update monitoring metrics
                monitoring.record_scan_duration(tier, name, "full_scan", time.time() - scan_start)
                
                # Record any vulnerabilities found
                for vuln in vuln_results:
                    monitoring.record_security_issue(tier, name, vuln.severity)
                
                # Update health score based on scan results
                health_score = 100 - (len(vuln_results) * 10) - (len(sast_results) * 5)
                monitoring.update_health_score(tier, name, max(0, health_score))
                
                scan = SecurityScan(
                    dependency_name=name,
                    version=version,
                    vulnerabilities=vuln_results,
                    sast_findings=sast_results,
                    risk_score=risk_score,
                    scan_date=datetime.utcnow()
                )
                
                # Update resource metrics
                monitoring.update_resource_metrics(tier, name)
                
                return scan
            
            except Exception as e:
                monitoring.log_error(tier, name, e)
                raise
                
    async def _check_vulnerabilities(self, name: str, version: str) -> List[Vulnerability]:
        """Check for known vulnerabilities in NVD database"""
        try:
            # Use nvdlib to query the NVD database
            vulns = []
            async with aiohttp.ClientSession() as session:
                params = {
                    "apiKey": self.nvd_api_key,
                    "keyword": name,
                    "versionStart": version,
                    "versionEnd": version
                }
                async with session.get(
                    "https://services.nvd.nist.gov/rest/json/cves/2.0",
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        for item in data.get("vulnerabilities", []):
                            vuln = item["cve"]
                            vulns.append(Vulnerability(
                                cve_id=vuln["id"],
                                description=vuln["description"]["description_data"][0]["value"],
                                severity=self._get_severity(vuln),
                                cvss_score=self._get_cvss_score(vuln),
                                affected_versions=[version],
                                fix_versions=self._get_fix_versions(vuln),
                                references=self._get_references(vuln),
                                discovered_date=datetime.utcnow()
                            ))
            return vulns
        except Exception as e:
            logger.error(f"Error checking vulnerabilities for {name}: {e}")
            return []
    
    async def _run_sast_scan(self, repo_path: str) -> List[Dict]:
        """Run Bandit SAST scan on Python code"""
        try:
            # Run Bandit scan in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor,
                self._execute_bandit_scan,
                repo_path
            )
        except Exception as e:
            logger.error(f"Error running SAST scan: {e}")
            return []
    
    def _execute_bandit_scan(self, repo_path: str) -> List[Dict]:
        """Execute Bandit scan and parse results"""
        # Create bandit config using the BanditConfig class 
        b_conf = b_config.BanditConfig()
        
        # Look for .bandit config in the repo path first, otherwise use defaults
        bandit_config_path = os.path.join(repo_path, ".bandit")
        if os.path.exists(bandit_config_path):
            try:
                with open(bandit_config_path) as f:
                    config_data = json.load(f)
                b_conf._config.update(config_data)
            except Exception as e:
                logger.warning(f"Failed to load .bandit config, using defaults: {e}")
                b_conf._config.update({
                    'plugin_name_pattern': '*.py',
                    'include': ['*.py'],
                    'exclude': ['tests', 'venv', '__pycache__', '.git'],
                    'profiles': {'All': {'include': [], 'exclude': []}}
                })
        else:
            b_conf._config.update({
                'plugin_name_pattern': '*.py',
                'include': ['*.py'], 
                'exclude': ['tests', 'venv', '__pycache__', '.git'],
                'profiles': {'All': {'include': [], 'exclude': []}}
            })
            
        # Initialize bandit manager with config and agg type
        mgr = bandit_manager.BanditManager(b_conf, 'file')
        
        if not os.path.exists(repo_path):
            logger.warning(f"Repository path does not exist: {repo_path}")
            return []
            
        # Also look in standard locations relative to repo_path
        paths_to_scan = [
            os.path.join(repo_path, 'src'),
            os.path.join(repo_path, 'lib'), 
            repo_path
        ]
        
        valid_paths = [p for p in paths_to_scan if os.path.exists(p)]
        if not valid_paths:
            logger.warning(f"No valid source paths found in {repo_path}")
            return []
        try:
            mgr.discover_files(valid_paths, ["*.py"])
            mgr.run_tests()
            
            results = []
            for issue in mgr.get_issue_list():
                results.append({
                    "severity": issue.severity,
                    "confidence": issue.confidence,
                    "description": issue.text,
                    "file": issue.fname,
                    "line": issue.lineno,
                    "test_id": issue.test_id
                })
            return results
        except Exception as e:
            logger.error(f"Error in bandit scan: {e}")
            return []
    
    def _calculate_risk_score(
        self,
        vulnerabilities: List[Vulnerability],
        sast_findings: List[Dict]
    ) -> float:
        """Calculate overall risk score based on findings"""
        vuln_score = sum(v.cvss_score for v in vulnerabilities)
        sast_score = sum(
            1.0 if f["severity"] == "HIGH" else
            0.5 if f["severity"] == "MEDIUM" else
            0.1
            for f in sast_findings
        )
        return min(10.0, vuln_score + sast_score)
    
    def _get_severity(self, vuln: Dict) -> str:
        """Extract severity from CVE data"""
        if "baseMetricV3" in vuln:
            return vuln["baseMetricV3"]["cvssV3"]["baseSeverity"]
        return "UNKNOWN"
    
    def _get_cvss_score(self, vuln: Dict) -> float:
        """Extract CVSS score from CVE data"""
        if "baseMetricV3" in vuln:
            return float(vuln["baseMetricV3"]["cvssV3"]["baseScore"])
        return 0.0
    
    def _get_fix_versions(self, vuln: Dict) -> List[str]:
        """Extract fix versions from CVE data"""
        try:
            return [
                ref["tags"][0]
                for ref in vuln.get("references", {}).get("reference_data", [])
                if "tags" in ref and "Version" in ref["tags"]
            ]
        except Exception:
            return []
    
    def _get_references(self, vuln: Dict) -> List[str]:
        """Extract references from CVE data"""
        try:
            return [
                ref["url"]
                for ref in vuln.get("references", {}).get("reference_data", [])
            ]
        except Exception:
            return []
    
    def _get_repo_path(self, repo_info: Dict) -> Optional[str]:
        """Get the local repository path from repo info"""
        # Try explicit repo_path first
        if "repo_path" in repo_info:
            path = os.path.expanduser(repo_info["repo_path"])
            if os.path.exists(path):
                return path
                
        # Try to find in standard locations based on name
        base_paths = [
            os.path.join(os.getcwd(), "repos"),  # ./repos/<name>
            os.path.join(os.getcwd(), "dependencies"),  # ./dependencies/<name>
            os.path.expanduser("~/Projects"),  # ~/Projects/<name>
        ]
        
        repo_name = repo_info.get("name", "").replace("/", "_").lower()
        for base in base_paths:
            path = os.path.join(base, repo_name)
            if os.path.exists(path):
                return path
                
        return None

    async def monitor_dependencies(self, dependencies: List[Dict]):
        """Continuous monitoring of dependencies for new vulnerabilities"""
        while True:
            try:
                for dep in dependencies:
                    try:
                        tier = dep.get("tier", "unknown")
                        name = dep["name"]
                        version = dep["version"]
                        
                        # Record monitoring iteration
                        monitoring.record_dependency_update(tier, name, "monitoring")
                        
                        scan_result = await self.scan_dependency(
                            name,
                            version, 
                            dep  # Pass full dependency info
                        )
                        
                        # Record and report any issues
                        if scan_result.vulnerabilities or scan_result.sast_findings:
                            await self._report_security_issues(scan_result)
                            monitoring.record_dependency_update(tier, name, "issues_found")
                        
                        # Update resource metrics after scan
                        monitoring.update_resource_metrics(tier, name)
                        
                    except Exception as e:
                        # Log individual dependency errors but continue monitoring others
                        monitoring.log_error(tier, name, e)
                        logger.error(f"Error monitoring dependency {name}: {e}")
                        continue
                        
                # Wait for 1 hour before next scan
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                # Wait shorter time before retry on error
                await asyncio.sleep(300)
                continue
    
    async def _report_security_issues(self, scan_result: SecurityScan):
        """Report security issues through notification service"""
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    "http://notification:8001/notify",
                    json={
                        "title": f"Security Issues Found: {scan_result.dependency_name}",
                        "message": self._format_security_report(scan_result),
                        "priority": "critical" if scan_result.risk_score >= 7.0 else "high",
                        "tier": 1,  # Security issues are always high priority
                        "details": {
                            "vulnerabilities": len(scan_result.vulnerabilities),
                            "sast_findings": len(scan_result.sast_findings),
                            "risk_score": scan_result.risk_score
                        }
                    }
                )
        except Exception as e:
            logger.error(f"Error reporting security issues: {e}")
    
    def _format_security_report(self, scan_result: SecurityScan) -> str:
        """Format security scan results for notification"""
        report = []
        report.append(f"Security Scan Results for {scan_result.dependency_name} v{scan_result.version}")
        report.append(f"Risk Score: {scan_result.risk_score:.1f}/10.0")
        
        if scan_result.vulnerabilities:
            report.append("\nVulnerabilities Found:")
            for vuln in scan_result.vulnerabilities:
                report.append(f"- {vuln.cve_id} (CVSS: {vuln.cvss_score})")
                report.append(f"  {vuln.description}")
        
        if scan_result.sast_findings:
            report.append("\nSAST Findings:")
            for finding in scan_result.sast_findings:
                report.append(
                    f"- {finding['severity']} ({finding['confidence']}): "
                    f"{finding['description']}"
                )
        
        return "\n".join(report)

async def main():
    """Main entry point"""
    security_service = SecurityService()
    
    # Load dependencies from config
    import os
    config_path = os.path.join(os.path.dirname(__file__), "dependencies.json")
    
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            dependencies = []
            for tier in config["tiers"].values():
                if "dependencies" in tier:
                    dependencies.extend(tier["dependencies"])
                else:
                    print(f"Warning: tier {tier['name']} has no dependencies configured")
    except FileNotFoundError:
        print(f"Error: Could not find {config_path}")
        print("Current directory:", os.getcwd())
        print("Directory contents:", os.listdir("."))
        raise
        
    # Start monitoring
    await security_service.monitor_dependencies(dependencies)

if __name__ == "__main__":
    asyncio.run(main())
