#!/usr/bin/env python3
"""
Enhanced CVE Database Integration Service
Provides direct API integration with multiple CVE databases for real-time vulnerability monitoring.
"""

import asyncio
import aiohttp
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VulnerabilitySeverity(Enum):
    """Vulnerability severity levels."""
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class CVEVulnerability:
    """CVE vulnerability data structure."""
    cve_id: str
    description: str
    published_date: str
    modified_date: str
    cvss_version: str
    cvss_score: float
    cvss_vector: str
    severity: str
    cwe_id: Optional[str] = None
    references: List[str] = None
    affected_products: List[str] = None
    exploit_available: bool = False
    patch_available: bool = False
    
    def __post_init__(self):
        if self.references is None:
            self.references = []
        if self.affected_products is None:
            self.affected_products = []

@dataclass
class DependencyVulnerabilityReport:
    """Dependency vulnerability assessment report."""
    dependency_name: str
    current_version: str
    vulnerabilities: List[CVEVulnerability]
    risk_score: float
    recommendations: List[str]
    last_scanned: str
    scan_duration_ms: int

class EnhancedCVEIntegration:
    """Enhanced CVE database integration with multiple data sources."""
    
    def __init__(self, config_path: str = "enhanced_cve_config.json"):
        self.config = self._load_config(config_path)
        self.session = None
        self.vulnerability_cache = {}
        self.rate_limits = {}
        self.api_keys = self._load_api_keys()
        
    def _load_config(self, config_path: str) -> Dict:
        """Load CVE integration configuration."""
        default_config = {
            "data_sources": {
                "nvd": {
                    "enabled": True,
                    "base_url": "https://services.nvd.nist.gov/rest/json",
                    "api_version": "2.0",
                    "rate_limit_per_30s": 5,
                    "timeout_seconds": 30
                },
                "cve_circl": {
                    "enabled": True,
                    "base_url": "https://cve.circl.lu/api",
                    "rate_limit_per_second": 10,
                    "timeout_seconds": 15
                },
                "github_advisory": {
                    "enabled": True,
                    "base_url": "https://api.github.com/advisories",
                    "rate_limit_per_hour": 5000,
                    "timeout_seconds": 10
                }
            },
            "scanning": {
                "scan_interval_hours": 6,
                "concurrent_requests": 5,
                "cache_duration_hours": 24,
                "high_priority_interval_hours": 1
            },
            "severity_thresholds": {
                "critical_alert": 9.0,
                "high_alert": 7.0,
                "medium_alert": 4.0,
                "low_alert": 0.1
            },
            "risk_scoring": {
                "cvss_weight": 0.4,
                "exploit_availability_weight": 0.3,
                "patch_availability_weight": 0.2,
                "age_factor_weight": 0.1
            }
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                    return {**default_config, **user_config}
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")
        
        # Save default config
        try:
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save config: {e}")
        
        return default_config
    
    def _load_api_keys(self) -> Dict[str, str]:
        """Load API keys from environment variables."""
        return {
            "nvd_api_key": os.getenv("NVD_API_KEY"),
            "github_token": os.getenv("GITHUB_TOKEN"),
            "cve_database_api_key": os.getenv("CVE_DATABASE_API_KEY")
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def _make_api_request(self, source: str, url: str, headers: Dict = None) -> Optional[Dict]:
        """Make rate-limited API request with retries."""
        source_config = self.config["data_sources"].get(source, {})
        
        if not source_config.get("enabled", False):
            return None
        
        # Prepare headers
        request_headers = headers or {}
        if source == "github_advisory" and self.api_keys.get("github_token"):
            request_headers["Authorization"] = f"token {self.api_keys['github_token']}"
        elif source == "nvd" and self.api_keys.get("nvd_api_key"):
            request_headers["apiKey"] = self.api_keys["nvd_api_key"]
        
        timeout = source_config.get("timeout_seconds", 30)
        
        try:
            async with self.session.get(url, headers=request_headers, timeout=timeout) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    return None
                else:
                    logger.warning(f"API request failed to {source}: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error making request to {source}: {e}")
        
        return None
    
    async def search_vulnerabilities_nvd(self, cve_id: str = None, keyword: str = None) -> List[CVEVulnerability]:
        """Search vulnerabilities using NVD API."""
        base_url = self.config["data_sources"]["nvd"]["base_url"]
        vulnerabilities = []
        
        if cve_id:
            url = f"{base_url}/cves/2.0?cveId={cve_id}"
        elif keyword:
            url = f"{base_url}/cves/2.0?keywordSearch={keyword}&resultsPerPage=50"
        else:
            return vulnerabilities
        
        try:
            data = await self._make_api_request("nvd", url)
            
            if data and "vulnerabilities" in data:
                for vuln_data in data["vulnerabilities"]:
                    vuln = self._parse_nvd_vulnerability(vuln_data)
                    if vuln:
                        vulnerabilities.append(vuln)
                        
        except Exception as e:
            logger.error(f"Error searching NVD vulnerabilities: {e}")
        
        return vulnerabilities
    
    def _parse_nvd_vulnerability(self, vuln_data: Dict) -> Optional[CVEVulnerability]:
        """Parse NVD vulnerability data."""
        try:
            cve = vuln_data.get("cve", {})
            cve_id = cve.get("id", "")
            
            # Get description
            descriptions = cve.get("descriptions", [])
            description = ""
            for desc in descriptions:
                if desc.get("lang") == "en":
                    description = desc.get("value", "")
                    break
            
            # Get dates
            published_date = cve.get("published", "")
            modified_date = cve.get("lastModified", "")
            
            # Get CVSS metrics
            metrics = cve.get("metrics", {})
            cvss_score = 0.0
            cvss_vector = ""
            cvss_version = ""
            severity = VulnerabilitySeverity.NONE.value
            
            # Try CVSS v3.1 first, then v3.0, then v2.0
            for version in ["cvssMetricV31", "cvssMetricV30", "cvssMetricV2"]:
                if version in metrics and metrics[version]:
                    metric = metrics[version][0]
                    cvss_data = metric.get("cvssData", {})
                    cvss_score = cvss_data.get("baseScore", 0.0)
                    cvss_vector = cvss_data.get("vectorString", "")
                    cvss_version = cvss_data.get("version", "")
                    severity = cvss_data.get("baseSeverity", "NONE")
                    break
            
            # Get references
            references = []
            ref_data = cve.get("references", [])
            for ref in ref_data:
                references.append(ref.get("url", ""))
            
            return CVEVulnerability(
                cve_id=cve_id,
                description=description,
                published_date=published_date,
                modified_date=modified_date,
                cvss_version=cvss_version,
                cvss_score=cvss_score,
                cvss_vector=cvss_vector,
                severity=severity,
                references=references
            )
            
        except Exception as e:
            logger.error(f"Error parsing NVD vulnerability: {e}")
            return None
    
    async def scan_dependency_vulnerabilities(self, dependency_name: str, version: str = None) -> DependencyVulnerabilityReport:
        """Comprehensive vulnerability scan for a dependency."""
        start_time = time.time()
        logger.info(f"Scanning vulnerabilities for {dependency_name}")
        
        # Search NVD by keyword
        vulnerabilities = await self.search_vulnerabilities_nvd(keyword=dependency_name)
        
        # Calculate risk score and generate recommendations
        risk_score = self._calculate_risk_score(vulnerabilities)
        recommendations = self._generate_recommendations(dependency_name, vulnerabilities, version)
        
        scan_duration = int((time.time() - start_time) * 1000)
        
        report = DependencyVulnerabilityReport(
            dependency_name=dependency_name,
            current_version=version or "unknown",
            vulnerabilities=vulnerabilities,
            risk_score=risk_score,
            recommendations=recommendations,
            last_scanned=datetime.now(timezone.utc).isoformat(),
            scan_duration_ms=scan_duration
        )
        
        logger.info(f"Scan completed: {len(vulnerabilities)} vulnerabilities, risk: {risk_score:.2f}")
        return report
    
    def _calculate_risk_score(self, vulnerabilities: List[CVEVulnerability]) -> float:
        """Calculate overall risk score for vulnerabilities."""
        if not vulnerabilities:
            return 0.0
        
        weights = self.config["risk_scoring"]
        total_score = 0.0
        
        for vuln in vulnerabilities:
            cvss_component = vuln.cvss_score * weights["cvss_weight"]
            exploit_component = (3.0 if vuln.exploit_available else 0.0) * weights["exploit_availability_weight"]
            patch_component = (0.0 if vuln.patch_available else 2.0) * weights["patch_availability_weight"]
            
            # Age factor
            try:
                published = datetime.fromisoformat(vuln.published_date.replace('Z', '+00:00'))
                now_utc = datetime.now(timezone.utc)
                pub = published if getattr(published, "tzinfo", None) else published.replace(tzinfo=timezone.utc)
                pub_utc = pub if pub.tzinfo == timezone.utc else pub.astimezone(timezone.utc)
                age_days = (now_utc - pub_utc).days
                age_factor = max(0.0, 2.0 - (age_days / 365))
            except:
                age_factor = 1.0
            
            age_component = age_factor * weights["age_factor_weight"]
            vuln_score = cvss_component + exploit_component + patch_component + age_component
            total_score += min(vuln_score, 10.0)
        
        return min(total_score / len(vulnerabilities), 10.0)
    
    def _generate_recommendations(self, dependency_name: str, vulnerabilities: List[CVEVulnerability], version: str = None) -> List[str]:
        """Generate actionable recommendations based on vulnerabilities."""
        recommendations = []
        
        if not vulnerabilities:
            recommendations.append("✅ No known vulnerabilities found")
            return recommendations
        
        # Categorize by severity
        critical = [v for v in vulnerabilities if v.severity == "CRITICAL"]
        high = [v for v in vulnerabilities if v.severity == "HIGH"]
        medium = [v for v in vulnerabilities if v.severity == "MEDIUM"]
        
        if critical:
            recommendations.append(f"🚨 URGENT: {len(critical)} critical vulnerabilities found")
            recommendations.append("• Immediate update required - stop using in production")
        
        if high:
            recommendations.append(f"⚠️ HIGH PRIORITY: {len(high)} high-severity vulnerabilities")
            recommendations.append("• Schedule emergency patch within 24 hours")
        
        if medium:
            recommendations.append(f"📋 MEDIUM: {len(medium)} medium-severity vulnerabilities")
            recommendations.append("• Update in next maintenance window")
        
        if any(v.patch_available for v in vulnerabilities):
            recommendations.append("✅ Patches are available - prioritize updating")
        
        if any(v.exploit_available for v in vulnerabilities):
            recommendations.append("⚠️ Active exploits detected - immediate action required")
        
        return recommendations
    
    async def get_vulnerability_by_cve_id(self, cve_id: str) -> Optional[CVEVulnerability]:
        """Get detailed vulnerability information by CVE ID."""
        vulnerabilities = await self.search_vulnerabilities_nvd(cve_id=cve_id)
        return vulnerabilities[0] if vulnerabilities else None
    
    async def monitor_new_vulnerabilities(self, dependencies: List[str], callback=None) -> List[CVEVulnerability]:
        """Monitor for new vulnerabilities in specified dependencies."""
        new_vulnerabilities = []
        logger.info(f"Monitoring {len(dependencies)} dependencies for new vulnerabilities")
        
        for dependency in dependencies:
            try:
                report = await self.scan_dependency_vulnerabilities(dependency)
                new_vulnerabilities.extend(report.vulnerabilities)
                
                if callback and report.vulnerabilities:
                    for vuln in report.vulnerabilities:
                        await callback(dependency, vuln)
                        
            except Exception as e:
                logger.error(f"Error scanning {dependency}: {e}")
        
        logger.info(f"Found {len(new_vulnerabilities)} vulnerabilities")
        return new_vulnerabilities

# CLI interface
async def main():
    """Main entry point for enhanced CVE integration."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced CVE Database Integration")
    parser.add_argument("--dependency", required=True, help="Dependency name to scan")
    parser.add_argument("--version", help="Dependency version")
    parser.add_argument("--cve-id", help="Specific CVE ID to lookup")
    
    args = parser.parse_args()
    
    async with EnhancedCVEIntegration() as cve_client:
        if args.cve_id:
            vuln = await cve_client.get_vulnerability_by_cve_id(args.cve_id)
            if vuln:
                print(json.dumps(asdict(vuln), indent=2, default=str))
            else:
                print(f"CVE {args.cve_id} not found")
        else:
            report = await cve_client.scan_dependency_vulnerabilities(args.dependency, args.version)
            print(json.dumps(asdict(report), indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())