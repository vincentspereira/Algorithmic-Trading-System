#!/usr/bin/env python3
"""
Demonstration script for EnvironmentManager

This script demonstrates the key functionality of the EnvironmentManager class,
showing how it validates the testing environment and dependencies.
"""

import sys
from pathlib import Path

# Add the framework directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from environment_manager import EnvironmentManager, ValidationStatus


def main():
    """Demonstrate EnvironmentManager functionality"""
    print("=" * 80)
    print("ENVIRONMENT MANAGER DEMONSTRATION")
    print("=" * 80)
    
    # Initialize EnvironmentManager
    print("\n1. Initializing EnvironmentManager...")
    env_manager = EnvironmentManager()
    print(f"   Project Root: {env_manager.project_root}")
    print(f"   Virtual Environment: {env_manager.venv_path}")
    print(f"   Requirements File: {env_manager.requirements_file}")
    print(f"   Python Executable: {env_manager.python_executable}")
    
    # Parse requirements file
    print("\n2. Parsing requirements.txt...")
    required_packages = env_manager._parse_requirements_file()
    print(f"   Found {len(required_packages)} required packages:")
    for package, version in list(required_packages.items())[:5]:  # Show first 5
        print(f"     - {package}: {version}")
    if len(required_packages) > 5:
        print(f"     ... and {len(required_packages) - 5} more")
    
    # Get installed packages
    print("\n3. Getting installed packages...")
    installed_packages = env_manager._get_installed_packages()
    print(f"   Found {len(installed_packages)} installed packages")
    
    # Validate dependencies
    print("\n4. Validating dependencies...")
    dependency_result = env_manager.validate_dependencies()
    print(f"   Status: {dependency_result.status.value}")
    print(f"   Total Dependencies: {dependency_result.total_dependencies}")
    print(f"   Validated Dependencies: {dependency_result.validated_dependencies}")
    print(f"   Missing Dependencies: {len(dependency_result.missing_dependencies)}")
    print(f"   Version Mismatches: {len(dependency_result.version_mismatches)}")
    
    if dependency_result.missing_dependencies:
        print("   Missing packages:")
        for package in dependency_result.missing_dependencies[:3]:
            print(f"     - {package}")
        if len(dependency_result.missing_dependencies) > 3:
            print(f"     ... and {len(dependency_result.missing_dependencies) - 3} more")
    
    if dependency_result.version_mismatches:
        print("   Version mismatches:")
        for dep in dependency_result.version_mismatches[:3]:
            print(f"     - {dep.name}: required {dep.required_version}, installed {dep.installed_version}")
        if len(dependency_result.version_mismatches) > 3:
            print(f"     ... and {len(dependency_result.version_mismatches) - 3} more")
    
    # Pip list comparison
    print("\n5. Performing pip list comparison...")
    pip_success, pip_results = env_manager.pip_list_comparison_and_validation()
    print(f"   Success: {pip_success}")
    if 'validation_summary' in pip_results:
        summary = pip_results['validation_summary']
        print(f"   Matching packages: {summary.get('match_count', 0)}")
        print(f"   Missing packages: {summary.get('missing_count', 0)}")
        print(f"   Version mismatches: {summary.get('mismatch_count', 0)}")
        print(f"   Extra packages: {summary.get('extra_count', 0)}")
    
    # Comprehensive validation
    print("\n6. Comprehensive environment validation...")
    validation_result = env_manager.comprehensive_environment_validation()
    print(f"   Overall Status: {validation_result.overall_status.value}")
    print(f"   Virtual Environment: {validation_result.virtual_env_status.value}")
    print(f"   Python Version: {validation_result.python_version_status.value}")
    print(f"   Path Validation: {validation_result.path_validation_status.value}")
    print(f"   Dependencies: {validation_result.dependencies_status.value}")
    
    if validation_result.error_messages:
        print("   Errors:")
        for error in validation_result.error_messages:
            print(f"     - {error}")
    
    if validation_result.warnings:
        print("   Warnings:")
        for warning in validation_result.warnings:
            print(f"     - {warning}")
    
    # Generate report
    print("\n7. Generating environment report...")
    report = env_manager.generate_environment_report()
    print("   Report generated successfully!")
    print(f"   Report length: {len(report)} characters")
    
    # Show summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if validation_result.overall_status == ValidationStatus.PASSED:
        print("✅ Environment validation PASSED - Ready for testing!")
    elif validation_result.overall_status == ValidationStatus.WARNING:
        print("⚠️  Environment validation has WARNINGS - Review before testing")
    else:
        print("❌ Environment validation FAILED - Issues must be resolved")
    
    print(f"\nDependency Status: {dependency_result.validated_dependencies}/{dependency_result.total_dependencies} validated")
    print(f"Pip Comparison: {'✅ PASSED' if pip_success else '❌ FAILED'}")
    
    # Optionally save the full report
    save_report = input("\nSave full environment report to file? (y/N): ").lower().strip()
    if save_report == 'y':
        report_file = Path("environment_validation_report.txt")
        report_file.write_text(report)
        print(f"Report saved to: {report_file.absolute()}")
    
    print("\nEnvironmentManager demonstration completed!")


if __name__ == "__main__":
    main()