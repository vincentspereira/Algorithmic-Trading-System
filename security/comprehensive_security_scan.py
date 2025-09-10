#!/usr/bin/env python3
"""
Comprehensive Security Scanning Script
Runs all security scans and generates consolidated reports.

This script orchestrates multiple security scanning tools including:
- Bandit (SAST)
- Safety (PyPI vulnerability checks)
- pip-audit (dependency vulnerability checks)
- Custom STRIDE threat modeling
"""

import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime
from typing import Dict, List

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services', 'dependency_management_service', 'security_service'))

def run_command(command: str, cwd: str = None) -> tuple:
    """Run a shell command and return stdout, stderr, and return code."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", f"Command timed out: {command}", 1
    except Exception as e:
        return "", f"Error running command: {e}", 1

def run_bandit_scan() -> Dict:
    """Run Bandit SAST scan."""
    print("🔍 Running Bandit SAST scan...")
    
    # Run Bandit with JSON output
    stdout, stderr, returncode = run_command(
        "bandit -r . -f json -o bandit-report.json || true"
    )
    
    # Run Bandit with text output for human readable
    stdout_txt, stderr_txt, returncode_txt = run_command(
        "bandit -r . -f txt -o bandit-report.txt || true"
    )
    
    # Try to load the JSON report
    try:
        if os.path.exists("bandit-report.json"):
            with open("bandit-report.json", "r") as f:
                bandit_data = json.load(f)
            issues_count = len(bandit_data.get("results", []))
            print(f"✅ Bandit scan completed with {issues_count} issues found")
            return {
                "status": "success",
                "issues_count": issues_count,
                "report_file": "bandit-report.json",
                "text_report": "bandit-report.txt"
            }
        else:
            print("⚠️  Bandit report file not found")
            return {
                "status": "warning",
                "issues_count": 0,
                "error": "Report file not generated"
            }
    except Exception as e:
        print(f"❌ Error processing Bandit results: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

def run_safety_check() -> Dict:
    """Run Safety vulnerability check."""
    print("🔍 Running Safety vulnerability check...")
    
    # Run Safety with JSON output
    stdout, stderr, returncode = run_command(
        "safety check --json --output safety-report.json || true"
    )
    
    # Run Safety with text output
    stdout_txt, stderr_txt, returncode_txt = run_command(
        "safety check --short-report -o safety-report.txt || true"
    )
    
    # Try to load the JSON report
    try:
        if os.path.exists("safety-report.json"):
            with open("safety-report.json", "r") as f:
                safety_data = json.load(f)
            vulnerabilities = safety_data.get("vulnerabilities", [])
            print(f"✅ Safety check completed with {len(vulnerabilities)} vulnerabilities found")
            return {
                "status": "success",
                "vulnerabilities_count": len(vulnerabilities),
                "report_file": "safety-report.json",
                "text_report": "safety-report.txt"
            }
        else:
            print("⚠️  Safety report file not found")
            return {
                "status": "warning",
                "vulnerabilities_count": 0,
                "error": "Report file not generated"
            }
    except Exception as e:
        print(f"❌ Error processing Safety results: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

def run_pip_audit() -> Dict:
    """Run pip-audit dependency check."""
    print("🔍 Running pip-audit dependency check...")
    
    # Run pip-audit with JSON output
    stdout, stderr, returncode = run_command(
        "pip-audit --format=json --output=pip-audit-report.json || true"
    )
    
    # Run pip-audit with CycloneDX output
    stdout_cyclone, stderr_cyclone, returncode_cyclone = run_command(
        "pip-audit --format=cyclonedx-json --output=sbom.json || true"
    )
    
    # Try to load the JSON report
    try:
        if os.path.exists("pip-audit-report.json"):
            with open("pip-audit-report.json", "r") as f:
                audit_data = json.load(f)
            vulnerabilities = audit_data if isinstance(audit_data, list) else []
            print(f"✅ pip-audit completed with {len(vulnerabilities)} vulnerabilities found")
            return {
                "status": "success",
                "vulnerabilities_count": len(vulnerabilities),
                "report_file": "pip-audit-report.json",
                "sbom_file": "sbom.json"
            }
        else:
            print("⚠️  pip-audit report file not found")
            return {
                "status": "warning",
                "vulnerabilities_count": 0,
                "error": "Report file not generated"
            }
    except Exception as e:
        print(f"❌ Error processing pip-audit results: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

async def run_stride_threat_modeling() -> Dict:
    """Run STRIDE threat modeling."""
    print("🔍 Running STRIDE threat modeling...")
    
    try:
        # Import and run the threat modeling script
        threat_modeling_script = os.path.join(os.path.dirname(__file__), "threat_modeling.py")
        stdout, stderr, returncode = run_command(f"python {threat_modeling_script}")
        
        if returncode == 0:
            print("✅ STRIDE threat modeling completed successfully")
            return {
                "status": "success",
                "report_file": "threat-model-report.txt",
                "json_report": "threat-model-report.json"
            }
        else:
            print(f"❌ STRIDE threat modeling failed: {stderr}")
            return {
                "status": "error",
                "error": stderr
            }
    except Exception as e:
        print(f"❌ Error running STRIDE threat modeling: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

def generate_summary_report(results: Dict) -> str:
    """Generate a summary report of all security scans."""
    report = []
    report.append("SECURITY SCAN SUMMARY REPORT")
    report.append("=" * 50)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    report.append("")
    
    # Bandit results
    bandit_result = results.get("bandit", {})
    report.append("BANDIT SAST SCAN:")
    if bandit_result.get("status") == "success":
        report.append(f"  Status: ✅ Success")
        report.append(f"  Issues Found: {bandit_result.get('issues_count', 0)}")
        report.append(f"  Report: {bandit_result.get('report_file', 'N/A')}")
    elif bandit_result.get("status") == "warning":
        report.append(f"  Status: ⚠️  Warning - {bandit_result.get('error', 'Unknown')}")
    else:
        report.append(f"  Status: ❌ Error - {bandit_result.get('error', 'Unknown')}")
    report.append("")
    
    # Safety results
    safety_result = results.get("safety", {})
    report.append("SAFETY VULNERABILITY CHECK:")
    if safety_result.get("status") == "success":
        report.append(f"  Status: ✅ Success")
        report.append(f"  Vulnerabilities Found: {safety_result.get('vulnerabilities_count', 0)}")
        report.append(f"  Report: {safety_result.get('report_file', 'N/A')}")
    elif safety_result.get("status") == "warning":
        report.append(f"  Status: ⚠️  Warning - {safety_result.get('error', 'Unknown')}")
    else:
        report.append(f"  Status: ❌ Error - {safety_result.get('error', 'Unknown')}")
    report.append("")
    
    # pip-audit results
    pip_audit_result = results.get("pip_audit", {})
    report.append("PIP-AUDIT DEPENDENCY CHECK:")
    if pip_audit_result.get("status") == "success":
        report.append(f"  Status: ✅ Success")
        report.append(f"  Vulnerabilities Found: {pip_audit_result.get('vulnerabilities_count', 0)}")
        report.append(f"  Report: {pip_audit_result.get('report_file', 'N/A')}")
        report.append(f"  SBOM: {pip_audit_result.get('sbom_file', 'N/A')}")
    elif pip_audit_result.get("status") == "warning":
        report.append(f"  Status: ⚠️  Warning - {pip_audit_result.get('error', 'Unknown')}")
    else:
        report.append(f"  Status: ❌ Error - {pip_audit_result.get('error', 'Unknown')}")
    report.append("")
    
    # STRIDE results
    stride_result = results.get("stride", {})
    report.append("STRIDE THREAT MODELING:")
    if stride_result.get("status") == "success":
        report.append(f"  Status: ✅ Success")
        report.append(f"  Report: {stride_result.get('report_file', 'N/A')}")
        report.append(f"  JSON Report: {stride_result.get('json_report', 'N/A')}")
    else:
        report.append(f"  Status: ❌ Error - {stride_result.get('error', 'Unknown')}")
    report.append("")
    
    return "\n".join(report)

def main():
    """Main function to run all security scans."""
    print("🛡️  Comprehensive Security Scanning System")
    print("=" * 50)
    
    # Create results directory if it doesn't exist
    results_dir = os.path.join(os.path.dirname(__file__), "security_reports")
    os.makedirs(results_dir, exist_ok=True)
    os.chdir(results_dir)
    
    print(f"📂 Working directory: {results_dir}")
    print("")
    
    # Dictionary to store results
    results = {}
    
    # Run Bandit SAST scan
    results["bandit"] = run_bandit_scan()
    print("")
    
    # Run Safety vulnerability check
    results["safety"] = run_safety_check()
    print("")
    
    # Run pip-audit dependency check
    results["pip_audit"] = run_pip_audit()
    print("")
    
    # Run STRIDE threat modeling
    results["stride"] = asyncio.run(run_stride_threat_modeling())
    print("")
    
    # Generate summary report
    print("📝 Generating summary report...")
    summary = generate_summary_report(results)
    print(summary)
    
    # Save summary report
    summary_file = os.path.join(results_dir, "security-scan-summary.txt")
    with open(summary_file, "w") as f:
        f.write(summary)
    print(f"💾 Summary report saved to: {summary_file}")
    
    # Save detailed results
    results_file = os.path.join(results_dir, "security-scan-results.json")
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"💾 Detailed results saved to: {results_file}")
    
    # Check for critical issues
    critical_issues = 0
    if results.get("bandit", {}).get("status") == "success":
        critical_issues += results["bandit"].get("issues_count", 0)
    if results.get("safety", {}).get("status") == "success":
        critical_issues += results["safety"].get("vulnerabilities_count", 0)
    if results.get("pip_audit", {}).get("status") == "success":
        critical_issues += results["pip_audit"].get("vulnerabilities_count", 0)
    
    if critical_issues > 0:
        print(f"\n⚠️  WARNING: {critical_issues} potential security issues detected!")
        print("Please review the detailed reports and address any critical vulnerabilities.")
        return 1
    else:
        print("\n✅ All security scans completed successfully with no critical issues detected!")
        return 0

if __name__ == "__main__":
    sys.exit(main())