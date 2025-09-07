#!/usr/bin/env python3
"""
Example usage of EnvironmentManager

This file shows how to use the EnvironmentManager class in different scenarios.
"""

import sys
from pathlib import Path

# Add the framework directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from environment_manager import EnvironmentManager, ValidationStatus


def basic_usage_example():
    """Basic usage example"""
    print("=== Basic Usage Example ===")
    
    # Create EnvironmentManager instance
    env_manager = EnvironmentManager()
    
    # Setup virtual environment
    if env_manager.setup_virtual_environment():
        print("✅ Virtual environment setup successful")
    else:
        print("❌ Virtual environment setup failed")
    
    # Validate dependencies
    result = env_manager.validate_dependencies()
    print(f"Dependencies: {result.validated_dependencies}/{result.total_dependencies} validated")
    
    # Generate report
    report = env_manager.generate_environment_report()
    print(f"Generated report with {len(report)} characters")


def comprehensive_validation_example():
    """Comprehensive validation example"""
    print("\n=== Comprehensive Validation Example ===")
    
    env_manager = EnvironmentManager()
    
    # Run comprehensive validation
    result = env_manager.comprehensive_environment_validation()
    
    print(f"Overall Status: {result.overall_status.value}")
    print(f"Virtual Environment: {result.virtual_env_status.value}")
    print(f"Dependencies: {result.dependencies_status.value}")
    
    if result.overall_status == ValidationStatus.PASSED:
        print("🎉 Environment is ready for testing!")
    else:
        print("⚠️ Environment needs attention before testing")
        
        if result.error_messages:
            print("Errors to fix:")
            for error in result.error_messages:
                print(f"  - {error}")


def dependency_management_example():
    """Dependency management example"""
    print("\n=== Dependency Management Example ===")
    
    env_manager = EnvironmentManager()
    
    # Check current dependencies
    result = env_manager.validate_dependencies()
    
    if result.missing_dependencies:
        print(f"Found {len(result.missing_dependencies)} missing dependencies:")
        for dep in result.missing_dependencies:
            print(f"  - {dep}")
        
        # Optionally install missing dependencies
        print("\nAttempting to install missing dependencies...")
        if env_manager.install_missing_dependencies():
            print("✅ Dependencies installed successfully")
            
            # Re-validate
            new_result = env_manager.validate_dependencies()
            print(f"After installation: {new_result.validated_dependencies}/{new_result.total_dependencies} validated")
        else:
            print("❌ Failed to install dependencies")
    else:
        print("✅ All dependencies are satisfied")


def pip_comparison_example():
    """Pip list comparison example"""
    print("\n=== Pip List Comparison Example ===")
    
    env_manager = EnvironmentManager()
    
    success, results = env_manager.pip_list_comparison_and_validation()
    
    print(f"Comparison successful: {success}")
    print(f"Total required: {results.get('total_required', 0)}")
    print(f"Total installed: {results.get('total_installed', 0)}")
    
    if 'validation_summary' in results:
        summary = results['validation_summary']
        print(f"Matching: {summary.get('match_count', 0)}")
        print(f"Missing: {summary.get('missing_count', 0)}")
        print(f"Mismatched: {summary.get('mismatch_count', 0)}")
        print(f"Extra: {summary.get('extra_count', 0)}")


def custom_project_example():
    """Example with custom project directory"""
    print("\n=== Custom Project Directory Example ===")
    
    # Use a specific project directory
    custom_project = Path("/path/to/custom/project")  # This would be a real path
    
    # For demo purposes, use current directory
    env_manager = EnvironmentManager(project_root=Path.cwd())
    
    print(f"Using project root: {env_manager.project_root}")
    print(f"Virtual environment: {env_manager.venv_path}")
    print(f"Requirements file: {env_manager.requirements_file}")
    
    # Validate paths
    path_status = env_manager._validate_paths()
    print(f"Path validation: {path_status.value}")


def error_handling_example():
    """Example showing error handling"""
    print("\n=== Error Handling Example ===")
    
    env_manager = EnvironmentManager()
    
    try:
        # This might fail if requirements.txt doesn't exist
        result = env_manager.validate_dependencies()
        
        if result.status == ValidationStatus.FAILED:
            print("Dependency validation failed, but handled gracefully")
            print(f"Missing: {len(result.missing_dependencies)} packages")
            print(f"Mismatched: {len(result.version_mismatches)} packages")
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        print("EnvironmentManager handles most errors gracefully")


if __name__ == "__main__":
    print("EnvironmentManager Usage Examples")
    print("=" * 50)
    
    basic_usage_example()
    comprehensive_validation_example()
    dependency_management_example()
    pip_comparison_example()
    custom_project_example()
    error_handling_example()
    
    print("\n" + "=" * 50)
    print("Examples completed!")