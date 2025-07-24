#!/usr/bin/env python3
"""
Quick Python Package Audit Script

This script provides immediate commands to safely audit your global Python packages.
Run this first to understand your current package state before any cleanup.
"""

import os
import sys
import json
import subprocess
import platform
from datetime import datetime

def run_command(cmd, description):
    """Run a command and display results safely."""
    print(f"\n{'='*60}")
    print(f"🔍 {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"❌ Error: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("⏰ Command timed out")
    except Exception as e:
        print(f"❌ Exception: {e}")

def create_immediate_backup():
    """Create an immediate backup of current package state."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    print(f"\n{'='*60}")
    print("💾 Creating Immediate Backup")
    print(f"{'='*60}")
    
    try:
        # Create requirements.txt backup
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'freeze'
        ], capture_output=True, text=True, check=True)
        
        backup_file = f'backup_requirements_{timestamp}.txt'
        with open(backup_file, 'w') as f:
            f.write(result.stdout)
        
        print(f"✅ Requirements backup created: {backup_file}")
        
        # Create JSON backup
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'list', '--format=json'
        ], capture_output=True, text=True, check=True)
        
        json_backup_file = f'backup_packages_{timestamp}.json'
        with open(json_backup_file, 'w') as f:
            f.write(result.stdout)
        
        print(f"✅ JSON backup created: {json_backup_file}")
        
        return backup_file, json_backup_file
        
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return None, None

def analyze_packages():
    """Analyze current package installation."""
    print(f"\n{'='*60}")
    print("📊 Package Analysis")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'list', '--format=json'
        ], capture_output=True, text=True, check=True)
        
        packages = json.loads(result.stdout)
        
        # Critical packages that should never be removed
        critical_packages = {
            'pip', 'setuptools', 'wheel', 'distutils', 'packaging', 'six',
            'certifi', 'urllib3', 'requests', 'charset-normalizer', 'idna',
            'python-dateutil', 'pytz'
        }
        
        critical_found = []
        user_packages = []
        total_packages = len(packages)
        
        for pkg in packages:
            if pkg['name'].lower() in critical_packages:
                critical_found.append(pkg['name'])
            else:
                user_packages.append(pkg['name'])
        
        print(f"📦 Total packages: {total_packages}")
        print(f"🛡️  Critical packages found: {len(critical_found)}")
        print(f"👤 Potential user packages: {len(user_packages)}")
        
        print(f"\n🛡️  Critical packages (protected):")
        for pkg in sorted(critical_found):
            print(f"   - {pkg}")
        
        if len(user_packages) > 20:
            print(f"\n👤 User packages (showing first 20 of {len(user_packages)}):")
            for pkg in sorted(user_packages)[:20]:
                print(f"   - {pkg}")
            print(f"   ... and {len(user_packages) - 20} more")
        else:
            print(f"\n👤 User packages:")
            for pkg in sorted(user_packages):
                print(f"   - {pkg}")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")

def show_python_info():
    """Show Python installation information."""
    print(f"\n{'='*60}")
    print("🐍 Python Installation Info")
    print(f"{'='*60}")
    
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Python Version: {sys.version}")
    print(f"Python Executable: {sys.executable}")
    
    # Show Python paths
    print(f"\nPython Paths:")
    for i, path in enumerate(sys.path):
        if path:  # Skip empty strings
            print(f"   {i+1}. {path}")
    
    # Show site packages
    try:
        import site
        print(f"\nSite Packages Directories:")
        for path in site.getsitepackages():
            print(f"   - {path}")
        
        user_site = site.getusersitepackages()
        print(f"\nUser Site Packages: {user_site}")
        
    except Exception as e:
        print(f"❌ Could not get site info: {e}")

def main():
    """Main audit function."""
    print("🔍 Python Package Quick Audit")
    print("=" * 60)
    print("This script will safely audit your Python installation")
    print("and create backups before any cleanup operations.")
    print("=" * 60)
    
    # Show Python info
    show_python_info()
    
    # Create backup first
    backup_req, backup_json = create_immediate_backup()
    
    # Basic package listing
    run_command([sys.executable, '-m', 'pip', 'list'], 
                "All Installed Packages")
    
    # Check for outdated packages
    run_command([sys.executable, '-m', 'pip', 'list', '--outdated'], 
                "Outdated Packages")
    
    # Check for broken packages
    run_command([sys.executable, '-m', 'pip', 'check'], 
                "Package Dependency Check")
    
    # Analyze packages
    analyze_packages()
    
    # Show next steps
    print(f"\n{'='*60}")
    print("🎯 Next Steps")
    print(f"{'='*60}")
    print("1. Review the package lists above")
    print("2. Identify packages you don't recognize or need")
    print("3. Run the interactive cleanup script:")
    print("   python scripts/cleanup_global_packages.py")
    print("4. Or manually remove specific packages:")
    print("   python -m pip uninstall package_name")
    
    if backup_req:
        print(f"\n💾 Your backups are saved as:")
        print(f"   - {backup_req}")
        if backup_json:
            print(f"   - {backup_json}")
    
    print(f"\n⚠️  Remember:")
    print("   - Never uninstall pip, setuptools, or wheel")
    print("   - Test in virtual environments when possible")
    print("   - Keep backups of your package state")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Audit cancelled by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")