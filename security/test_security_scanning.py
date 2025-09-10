#!/usr/bin/env python3
"""
Test script for the comprehensive security scanning implementation.
"""

import os
import sys
import subprocess
import json
from datetime import datetime

def test_script_execution():
    """Test that the security scanning script can be executed."""
    print("🧪 Testing security scanning script execution...")
    
    try:
        # Change to the security directory
        security_dir = os.path.dirname(__file__)
        os.chdir(security_dir)
        
        # Run the security scanning script
        result = subprocess.run(
            ["python", "comprehensive_security_scan.py"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print(f"Return code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
        
        # Check if reports were generated
        reports_dir = os.path.join(security_dir, "security_reports")
        if os.path.exists(reports_dir):
            print("✅ Security reports directory created")
            files = os.listdir(reports_dir)
            print(f"Files in reports directory: {files}")
            
            # Check for specific report files
            expected_files = [
                "security-scan-summary.txt",
                "security-scan-results.json"
            ]
            
            for expected_file in expected_files:
                if expected_file in files:
                    print(f"✅ {expected_file} generated successfully")
                else:
                    print(f"⚠️  {expected_file} not found")
        else:
            print("❌ Security reports directory not created")
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Security scanning script timed out")
        return False
    except Exception as e:
        print(f"❌ Error testing security scanning script: {e}")
        return False

def test_threat_modeling():
    """Test the threat modeling script."""
    print("\n🧪 Testing threat modeling script...")
    
    try:
        # Change to the security directory
        security_dir = os.path.dirname(__file__)
        os.chdir(security_dir)
        
        # Run the threat modeling script
        result = subprocess.run(
            ["python", "threat_modeling.py"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"Return code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
        
        # Check if threat model reports were generated
        expected_files = [
            "threat-model-report.txt",
            "threat-model-report.json"
        ]
        
        for expected_file in expected_files:
            if os.path.exists(expected_file):
                print(f"✅ {expected_file} generated successfully")
                # Show first few lines of the report
                with open(expected_file, 'r') as f:
                    content = f.read()
                    print(f"Sample content from {expected_file}:")
                    print(content[:500] + "..." if len(content) > 500 else content)
            else:
                print(f"⚠️  {expected_file} not found")
                
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Threat modeling script timed out")
        return False
    except Exception as e:
        print(f"❌ Error testing threat modeling script: {e}")
        return False

def test_docker_build():
    """Test that the security Dockerfile can be built."""
    print("\n🧪 Testing security Dockerfile build...")
    
    try:
        # Change to the project root directory
        project_root = os.path.join(os.path.dirname(__file__), "..")
        os.chdir(project_root)
        
        # Build the security Docker image
        result = subprocess.run(
            ["docker", "build", "-t", "security-scanner", "-f", "security/Dockerfile", "."],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        print(f"Return code: {result.returncode}")
        if result.stdout:
            print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
            
        if result.returncode == 0:
            print("✅ Security Docker image built successfully")
        else:
            print("❌ Security Docker image build failed")
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Docker build timed out")
        return False
    except Exception as e:
        print(f"❌ Error testing Docker build: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 Security Scanning Implementation Test")
    print("=" * 50)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run all tests
    tests = [
        ("Security Scanning Script", test_script_execution),
        ("Threat Modeling Script", test_threat_modeling),
        ("Docker Build", test_docker_build)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name} test...")
        try:
            result = test_func()
            results.append((test_name, result))
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name} test")
        except Exception as e:
            print(f"❌ ERROR in {test_name} test: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n📈 Total: {len(results)} tests")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 All security scanning tests passed!")
        print("The security scanning implementation is working correctly.")
        return 0
    else:
        print("\n⚠️  Some security scanning tests failed.")
        print("Please review the output above and fix any issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())