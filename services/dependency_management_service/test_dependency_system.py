#!/usr/bin/env python3
"""
Test script for validating the dependency management system.
"""

import json
import os
import sys
from pathlib import Path

def test_tier_files_exist():
    """Test that all tier files exist."""
    tier_files = [
        '../../dependency_management/tiers/tier1_critical.json',
        '../../dependency_management/tiers/tier2_important.json',
        '../../dependency_management/tiers/tier3_supporting.json',
        '../../dependency_management/tiers/tier4_infrastructure.json'
    ]
    
    print("Testing tier files...")
    for tier_file in tier_files:
        if Path(tier_file).exists():
            print(f"  ✓ {tier_file} exists")
            
            # Load and validate JSON structure
            try:
                with open(tier_file, 'r') as f:
                    data = json.load(f)
                
                assert 'tier' in data, f"Missing 'tier' in {tier_file}"
                assert 'name' in data, f"Missing 'name' in {tier_file}"
                assert 'dependencies' in data, f"Missing 'dependencies' in {tier_file}"
                
                print(f"    ✓ JSON structure valid")
                
                # Check dependencies structure
                for dep in data['dependencies']:
                    assert 'name' in dep, f"Missing 'name' in dependency in {tier_file}"
                    assert 'type' in dep, f"Missing 'type' in dependency {dep['name']} in {tier_file}"
                    assert 'criticality' in dep, f"Missing 'criticality' in dependency {dep['name']} in {tier_file}"
                    
                print(f"    ✓ Dependencies structure valid")
            except Exception as e:
                print(f"  ✗ Error validating {tier_file}: {e}")
                return False
        else:
            print(f"  ✗ {tier_file} does not exist")
            return False
    
    return True

def test_config_files_exist():
    """Test that configuration files exist."""
    config_files = [
        '../../dependency_management/monitoring/dependency_monitor.yml',
        '../../dependency_management/monitoring/check_dependencies.py',
        '../../dependency_management/notifications/notification_config.json',
        '../../dependency_management/testing/docker-compose.test.yml',
        '../../dependency_management/dashboards/dependency_health_dashboard.json',
        '../../dependency_management/security/bandit_config.yaml',
        '../../dependency_management/customization_tracking.json'
    ]
    
    print("\nTesting configuration files...")
    for config_file in config_files:
        if Path(config_file).exists():
            print(f"  ✓ {config_file} exists")
        else:
            print(f"  ✗ {config_file} does not exist")
            return False
    
    return True

def test_documentation_files_exist():
    """Test that documentation files exist."""
    doc_files = [
        '../../dependency_management/README.md',
        '../../dependency_management/tiers/README.md',
        '../../dependency_management/placeholder_protocol.md',
        '../../dependency_management/incremental_development_protocol.md'
    ]
    
    print("\nTesting documentation files...")
    for doc_file in doc_files:
        if Path(doc_file).exists():
            print(f"  ✓ {doc_file} exists")
        else:
            print(f"  ✗ {doc_file} does not exist")
            return False
    
    return True

def test_updated_main_documentation():
    """Test that the main dependency management documentation was updated."""
    main_doc = '../../docs/DEPENDENCY_MANAGEMENT.md'
    
    print("\nTesting main documentation update...")
    if Path(main_doc).exists():
        print(f"  ✓ {main_doc} exists")
        
        # Check if it contains updated content
        with open(main_doc, 'r') as f:
            content = f.read()
            
        if "Dependency Tiers" in content and "Dependency Management System" in content:
            print("  ✓ Main documentation contains updated content")
            return True
        else:
            print("  ✗ Main documentation does not contain expected updated content")
            return False
    else:
        print(f"  ✗ {main_doc} does not exist")
        return False

def main():
    """Main test function."""
    print("Running Dependency Management System Tests...\n")
    
    tests = [
        test_tier_files_exist,
        test_config_files_exist,
        test_documentation_files_exist,
        test_updated_main_documentation
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ✗ Test {test.__name__} failed with exception: {e}")
            failed += 1
    
    print(f"\nTest Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✓ All tests passed! Dependency Management System is properly configured.")
        return 0
    else:
        print("✗ Some tests failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())