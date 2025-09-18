"""
Dependency monitoring system with tier-specific schedules.
Handles automated monitoring, vulnerability scanning, and status tracking.
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set
import requests
from croniter import croniter

from .repository_manager import RepositoryManager

logger = logging.getLogger(__name__)

@dataclass
class VulnerabilityInfo:
    """Information about a security vulnerability"""
    id: str
    severity: str
    description: str
    affected_versions: List[str]
    fix_versions: List[str]
    cve_ids: List[str]
    discovered_date: str

@dataclass
class UpdateInfo:
    """Information about a dependency update"""
    current_version: str
    latest_version: str
    changelog_url: str
    breaking_changes: bool
    security_fixes: bool
    performance_improvements: bool
    release_date: str

@dataclass
class DependencyStatus:
    """Current status of a dependency"""
    name: str
    tier: str
    last_check: datetime
    last_update: datetime
    current_commit: str
    vulnerabilities: List[VulnerabilityInfo]
    available_update: Optional[UpdateInfo] = None
    health_status: str = "healthy"
    error_count: int = 0

class DependencyMonitor:
    """Monitors dependencies based on their tier configuration"""
    
    def __init__(
        self,
        config_path: str,
        github_token: str,
        nvd_api_key: str
    ):
        self.config_path = Path(config_path)
        self.github_token = github_token
        self.nvd_api_key = nvd_api_key
        self.repo_manager = RepositoryManager(config_path, github_token)
        self.status_cache: Dict[str, DependencyStatus] = {}
        self.last_run: Dict[str, datetime] = {}
        
    def _get_headers(self, api_type: str = "github") -> Dict[str, str]:
        """Get API headers based on type"""
        if api_type == "github":
            return {
                "Authorization": f"Bearer {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
        elif api_type == "nvd":
            return {
                "apiKey": self.nvd_api_key
            }
        return {}
        
    def _should_run(self, schedule: str, last_run: datetime) -> bool:
        """Check if monitoring should run based on schedule"""
        if not last_run:
            return True
            
        cron = croniter(schedule, last_run)
        next_run = cron.get_next(datetime)
        # Ensure next_run is timezone-aware (UTC)
        if next_run.tzinfo is None or next_run.tzinfo.utcoffset(next_run) is None:
            next_run = next_run.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= next_run
        
    def check_vulnerabilities(
        self,
        dependency: Dict
    ) -> List[VulnerabilityInfo]:
        """Check for vulnerabilities using GitHub and NVD APIs"""
        vulnerabilities = []
        
        try:
            # Check GitHub Security Advisories
            url = f"https://api.github.com/repos/{dependency['fork']}/vulnerability-alerts"
            headers = {
                **self._get_headers("github"),
                "Accept": "application/vnd.github.dorian-preview+json"
            }
            
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                for alert in response.json():
                    vuln = VulnerabilityInfo(
                        id=alert["id"],
                        severity=alert["severity"],
                        description=alert["description"],
                        affected_versions=alert["affected_versions"],
                        fix_versions=alert["fixed_versions"],
                        cve_ids=alert.get("cve_ids", []),
                        discovered_date=alert["created_at"]
                    )
                    vulnerabilities.append(vuln)
                    
            # Check NVD Database
            if dependency.get("cpe"):
                url = f"https://services.nvd.nist.gov/rest/json/cves/2.0"
                params = {
                    "cpeName": dependency["cpe"],
                    "lastModStartDate": (
                        datetime.now(timezone.utc) - timedelta(days=30)
                    ).strftime("%Y-%m-%dT%H:%M:%S:000 UTC-00:00")
                }
                
                response = requests.get(
                    url,
                    headers=self._get_headers("nvd"),
                    params=params
                )
                
                if response.status_code == 200:
                    for cve in response.json()["vulnerabilities"]:
                        if not any(v.id == cve["cve"]["id"] for v in vulnerabilities):
                            vuln = VulnerabilityInfo(
                                id=cve["cve"]["id"],
                                severity=cve["cve"]["metrics"].get(
                                    "baseMetricV3",
                                    {}
                                ).get("cvssV3", {}).get("baseSeverity", "UNKNOWN"),
                                description=cve["cve"]["description"]["description_data"][0]["value"],
                                affected_versions=cve["cve"]["affects"]["vendor"]["vendor_data"][0]["product"]["version"],
                                fix_versions=[],
                                cve_ids=[cve["cve"]["id"]],
                                discovered_date=cve["publishedDate"]
                            )
                            vulnerabilities.append(vuln)
                            
        except Exception as e:
            logger.error(
                f"Error checking vulnerabilities for {dependency['name']}: {str(e)}"
            )
            
        return vulnerabilities
        
    def check_updates(
        self,
        dependency: Dict
    ) -> Optional[UpdateInfo]:
        """Check for available updates"""
        try:
            # Get latest release
            url = f"https://api.github.com/repos/{dependency['repo']}/releases/latest"
            response = requests.get(url, headers=self._get_headers())
            
            if response.status_code == 200:
                release = response.json()
                
                # Get current version from fork
                url = f"https://api.github.com/repos/{dependency['fork']}/releases/latest"
                curr_response = requests.get(url, headers=self._get_headers())
                current_version = "unknown"
                
                if curr_response.status_code == 200:
                    current_version = curr_response.json()["tag_name"]
                    
                return UpdateInfo(
                    current_version=current_version,
                    latest_version=release["tag_name"],
                    changelog_url=release["html_url"],
                    breaking_changes="BREAKING CHANGE" in release["body"],
                    security_fixes="security" in release["body"].lower(),
                    performance_improvements="performance" in release["body"].lower(),
                    release_date=release["published_at"]
                )
                
        except Exception as e:
            logger.error(
                f"Error checking updates for {dependency['name']}: {str(e)}"
            )
            
        return None
        
    def monitor_dependency(
        self,
        tier: str,
        dependency: Dict
    ) -> DependencyStatus:
        """Monitor a single dependency"""
        try:
            # Check repository status
            status = self.repo_manager.get_dependency_status(dependency["fork"])
            
            if not status:
                return DependencyStatus(
                    name=dependency["name"],
                    tier=tier,
                    last_check=datetime.now(timezone.utc),
                    last_update=datetime.min.replace(tzinfo=timezone.utc),
                    current_commit="unknown",
                    vulnerabilities=[],
                    health_status="error"
                )
                
            # Check vulnerabilities
            vulnerabilities = self.check_vulnerabilities(dependency)
            
            # Check for updates
            update_info = self.check_updates(dependency)
            
            # Determine health status
            health_status = "healthy"
            if vulnerabilities:
                if any(v.severity in ("CRITICAL", "HIGH") for v in vulnerabilities):
                    health_status = "critical"
                else:
                    health_status = "warning"
                    
            return DependencyStatus(
                name=dependency["name"],
                tier=tier,
                last_check=datetime.now(timezone.utc),
                last_update=datetime.fromisoformat(
                    status["last_checked"].replace("Z", "+00:00")
                ),
                current_commit=status["latest_commit"],
                vulnerabilities=vulnerabilities,
                available_update=update_info,
                health_status=health_status
            )
            
        except Exception as e:
            logger.error(
                f"Error monitoring {dependency['name']}: {str(e)}"
            )
            return DependencyStatus(
                name=dependency["name"],
                tier=tier,
                last_check=datetime.now(timezone.utc),
                last_update=datetime.min.replace(tzinfo=timezone.utc),
                current_commit="unknown",
                vulnerabilities=[],
                health_status="error",
                error_count=1
            )
            
    def monitor_tier(
        self,
        tier: str,
        config: Dict
    ) -> List[DependencyStatus]:
        """Monitor all dependencies in a tier"""
        results = []
        
        # Check if we should run based on schedule
        schedule = self.repo_manager.config["monitoring_config"]["update_check"]["schedule"][tier]
        last_run = self.last_run.get(tier)
        
        if not self._should_run(schedule, last_run):
            # Return cached results if available
            return [
                status for status in self.status_cache.values()
                if status.tier == tier
            ]
            
        for dependency in config["dependencies"]:
            status = self.monitor_dependency(tier, dependency)
            self.status_cache[f"{tier}/{dependency['name']}"] = status
            results.append(status)
            
        self.last_run[tier] = datetime.now(timezone.utc)
        return results
        
    def monitor_all(self) -> Dict[str, List[DependencyStatus]]:
        """Monitor all dependencies across all tiers"""
        results = {}
        
        for tier, config in self.repo_manager.config["tiers"].items():
            results[tier] = self.monitor_tier(tier, config)
            
        return results
        
    def get_critical_issues(self) -> List[Dict]:
        """Get list of critical issues across all dependencies"""
        critical = []
        
        for status in self.status_cache.values():
            # Check for critical vulnerabilities
            critical_vulns = [
                v for v in status.vulnerabilities
                if v.severity in ("CRITICAL", "HIGH")
            ]
            
            if critical_vulns:
                critical.append({
                    "dependency": status.name,
                    "tier": status.tier,
                    "type": "vulnerability",
                    "details": critical_vulns
                })
                
            # Check for breaking changes
            if (
                status.available_update and
                status.available_update.breaking_changes
            ):
                critical.append({
                    "dependency": status.name,
                    "tier": status.tier,
                    "type": "breaking_change",
                    "details": status.available_update
                })
                
            # Check for errors
            if status.health_status == "error":
                critical.append({
                    "dependency": status.name,
                    "tier": status.tier,
                    "type": "error",
                    "details": f"Error count: {status.error_count}"
                })
                
        return critical
        
def main():
    """Main entry point for dependency monitoring"""
    logging.basicConfig(level=logging.INFO)
    
    config_path = os.getenv(
        "REPO_CONFIG",
        "config/repository_management.json"
    )
    github_token = os.getenv("GITHUB_TOKEN")
    nvd_api_key = os.getenv("NVD_API_KEY")
    
    if not github_token:
        raise ValueError("GITHUB_TOKEN environment variable not set")
        
    if not nvd_api_key:
        raise ValueError("NVD_API_KEY environment variable not set")
        
    monitor = DependencyMonitor(config_path, github_token, nvd_api_key)
    
    # Run initial monitoring
    results = monitor.monitor_all()
    
    # Check for critical issues
    critical = monitor.get_critical_issues()
    if critical:
        logger.warning(f"Found {len(critical)} critical issues")
        for issue in critical:
            logger.warning(
                f"{issue['dependency']} ({issue['tier']}): "
                f"{issue['type']} - {issue['details']}"
            )
            
if __name__ == "__main__":
    main()
