#!/usr/bin/env python3
"""
Safe Global Python Package Cleanup Script

This script helps safely identify and remove globally installed Python packages
while protecting system-critical packages and providing backup functionality.

IMPORTANT: Always review the package list before proceeding with any removals!
"""

import os
import sys
import json
import subprocess
import platform
from datetime import datetime
from pathlib import Path
import pkg_resources

# System-critical packages that should NEVER be uninstalled
CRITICAL_PACKAGES = {
    'pip', 'setuptools', 'wheel', 'distutils', 'packaging', 'six',
    'certifi', 'urllib3', 'requests', 'charset-normalizer', 'idna',
    'python-dateutil', 'pytz', 'numpy', 'scipy'  # Common system dependencies
}

# Common system package prefixes (packages installed by OS package managers)
SYSTEM_PACKAGE_PREFIXES = {
    'python3-', 'python-', 'lib', 'system-'
}

def get_system_info():
    """Get system information for context."""
    return {
        'platform': platform.system(),
        'python_version': sys.version,
        'python_executable': sys.executable,
        'timestamp': datetime.now().isoformat()
    }

def get_all_packages():
    """Get all installed packages with their information."""
    packages = []
    
    try:
        # Use pip list to get comprehensive package information
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'list', '--format=json'
        ], capture_output=True, text=True, check=True)
        
        pip_packages = json.loads(result.stdout)
        
        for pkg in pip_packages:
            try:
                # Get additional package information
                dist = pkg_resources.get_distribution(pkg['name'])
                location = dist.location if hasattr(dist, 'location') else 'Unknown'
                
                # Determine if package is likely user-installed
                is_user_installed = is_likely_user_package(pkg['name'], location)
                is_critical = pkg['name'].lower() in CRITICAL_PACKAGES
                
                packages.append({
                    'name': pkg['name'],
                    'version': pkg['version'],
                    'location': location,
                    'is_user_installed': is_user_installed,
                    'is_critical': is_critical,
                    'is_editable': '-e ' in str(dist) if dist else False
                })
            except Exception as e:
                # If we can't get detailed info, still include basic info
                packages.append({
                    'name': pkg['name'],
                    'version': pkg['version'],
                    'location': 'Unknown',
                    'is_user_installed': False,
                    'is_critical': pkg['name'].lower() in CRITICAL_PACKAGES,
                    'is_editable': False,
                    'error': str(e)
                })
                
    except subprocess.CalledProcessError as e:
        print(f"Error getting package list: {e}")
        return []
    
    return packages

def is_likely_user_package(package_name, location):
    """Determine if a package is likely user-installed vs system-installed."""
    package_lower = package_name.lower()
    
    # Check if it's a system package by name
    for prefix in SYSTEM_PACKAGE_PREFIXES:
        if package_lower.startswith(prefix):
            return False
    
    # Check location patterns
    if location and isinstance(location, str):
        location_lower = location.lower()
        
        # System locations (common patterns)
        system_patterns = [
            '/usr/lib/python',
            '/usr/local/lib/python',
            'c:\\python',
            'c:\\program files',
            '/system/',
            '/library/frameworks/python',
            'site-packages' in location_lower and 'users' not in location_lower
        ]
        
        # User locations (common patterns)
        user_patterns = [
            'users',
            'home',
            '.local',
            'appdata',
            'roaming'
        ]
        
        # Check for user patterns first
        for pattern in user_patterns:
            if pattern in location_lower:
                return True
                
        # Check for system patterns
        for pattern in system_patterns:
            if isinstance(pattern, str) and pattern in location_lower:
                return False
            elif isinstance(pattern, bool) and pattern:
                return False
    
    # Default to user-installed if uncertain
    return True

def create_backup(packages, backup_dir='backups'):
    """Create a backup of current package state."""
    backup_path = Path(backup_dir)
    backup_path.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = backup_path / f'python_packages_backup_{timestamp}.json'
    
    backup_data = {
        'system_info': get_system_info(),
        'packages': packages,
        'requirements_format': [f"{pkg['name']}=={pkg['version']}" for pkg in packages]
    }
    
    with open(backup_file, 'w') as f:
        json.dump(backup_data, f, indent=2)
    
    print(f"✅ Backup created: {backup_file}")
    return backup_file

def display_packages(packages, filter_type='all'):
    """Display packages in a formatted table."""
    if filter_type == 'user':
        filtered_packages = [p for p in packages if p['is_user_installed'] and not p['is_critical']]
        title = "User-Installed Packages (Safe to Remove)"
    elif filter_type == 'critical':
        filtered_packages = [p for p in packages if p['is_critical']]
        title = "Critical Packages (DO NOT REMOVE)"
    elif filter_type == 'system':
        filtered_packages = [p for p in packages if not p['is_user_installed']]
        title = "System Packages"
    else:
        filtered_packages = packages
        title = "All Packages"
    
    print(f"\n{'='*80}")
    print(f"{title} ({len(filtered_packages)} packages)")
    print(f"{'='*80}")
    
    if not filtered_packages:
        print("No packages found in this category.")
        return
    
    # Header
    print(f"{'#':<3} {'Package':<25} {'Version':<15} {'Location':<35}")
    print(f"{'-'*3} {'-'*25} {'-'*15} {'-'*35}")
    
    for i, pkg in enumerate(filtered_packages, 1):
        status = ""
        if pkg['is_critical']:
            status = " ⚠️ CRITICAL"
        elif pkg['is_editable']:
            status = " 📝 EDITABLE"
        
        location = pkg['location'][:32] + "..." if len(pkg['location']) > 35 else pkg['location']
        
        print(f"{i:<3} {pkg['name']:<25} {pkg['version']:<15} {location:<35}{status}")

def interactive_removal(packages):
    """Interactive package removal with safety checks."""
    user_packages = [p for p in packages if p['is_user_installed'] and not p['is_critical']]
    
    if not user_packages:
        print("\n❌ No safe user packages found for removal.")
        return
    
    print(f"\n🔍 Found {len(user_packages)} user-installed packages that are safe to remove.")
    
    while True:
        print("\nOptions:")
        print("1. Remove all user packages")
        print("2. Select specific packages to remove")
        print("3. Show package details")
        print("4. Exit without changes")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            confirm = input(f"\n⚠️  Remove ALL {len(user_packages)} user packages? (yes/no): ").strip().lower()
            if confirm == 'yes':
                remove_packages([pkg['name'] for pkg in user_packages])
            break
            
        elif choice == '2':
            selected_packages = select_packages_interactive(user_packages)
            if selected_packages:
                remove_packages(selected_packages)
            break
            
        elif choice == '3':
            display_packages(user_packages, 'user')
            
        elif choice == '4':
            print("Exiting without making changes.")
            break
            
        else:
            print("Invalid choice. Please enter 1-4.")

def select_packages_interactive(packages):
    """Allow user to select specific packages for removal."""
    display_packages(packages, 'user')
    
    print(f"\nEnter package numbers to remove (e.g., 1,3,5-8) or 'all' for all packages:")
    print("Enter 'none' or empty to cancel.")
    
    selection = input("Selection: ").strip()
    
    if not selection or selection.lower() == 'none':
        return []
    
    if selection.lower() == 'all':
        return [pkg['name'] for pkg in packages]
    
    selected_indices = parse_selection(selection, len(packages))
    selected_packages = [packages[i-1]['name'] for i in selected_indices if 1 <= i <= len(packages)]
    
    if selected_packages:
        print(f"\nSelected packages: {', '.join(selected_packages)}")
        confirm = input("Proceed with removal? (yes/no): ").strip().lower()
        if confirm == 'yes':
            return selected_packages
    
    return []

def parse_selection(selection, max_num):
    """Parse user selection string into list of indices."""
    indices = set()
    
    for part in selection.split(','):
        part = part.strip()
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                indices.update(range(start, end + 1))
            except ValueError:
                continue
        else:
            try:
                indices.add(int(part))
            except ValueError:
                continue
    
    return sorted([i for i in indices if 1 <= i <= max_num])

def remove_packages(package_names):
    """Remove specified packages."""
    if not package_names:
        return
    
    print(f"\n🗑️  Removing {len(package_names)} packages...")
    
    for package in package_names:
        try:
            print(f"Removing {package}...")
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'uninstall', package, '-y'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ Successfully removed {package}")
            else:
                print(f"❌ Failed to remove {package}: {result.stderr}")
                
        except Exception as e:
            print(f"❌ Error removing {package}: {e}")
    
    print("\n✅ Package removal completed.")

def main():
    """Main function."""
    print("🐍 Python Global Package Cleanup Tool")
    print("=====================================")
    
    # Get system info
    system_info = get_system_info()
    print(f"Platform: {system_info['platform']}")
    print(f"Python: {system_info['python_version'].split()[0]}")
    print(f"Executable: {system_info['python_executable']}")
    
    # Get all packages
    print("\n📦 Scanning installed packages...")
    packages = get_all_packages()
    
    if not packages:
        print("❌ No packages found or error occurred.")
        return
    
    print(f"Found {len(packages)} total packages")
    
    # Create backup
    print("\n💾 Creating backup...")
    backup_file = create_backup(packages)
    
    # Show package categories
    user_packages = [p for p in packages if p['is_user_installed'] and not p['is_critical']]
    critical_packages = [p for p in packages if p['is_critical']]
    system_packages = [p for p in packages if not p['is_user_installed']]
    
    print(f"\n📊 Package Summary:")
    print(f"   Total packages: {len(packages)}")
    print(f"   User packages (safe to remove): {len(user_packages)}")
    print(f"   Critical packages (protected): {len(critical_packages)}")
    print(f"   System packages: {len(system_packages)}")
    
    while True:
        print(f"\n{'='*50}")
        print("What would you like to do?")
        print("1. View all packages")
        print("2. View user packages only")
        print("3. View critical packages (protected)")
        print("4. View system packages")
        print("5. Start interactive removal")
        print("6. Export package list to requirements.txt")
        print("7. Show Docker usage instructions")
        print("8. Exit")
        
        choice = input("\nEnter your choice (1-8): ").strip()
        
        if choice == '1':
            display_packages(packages, 'all')
        elif choice == '2':
            display_packages(packages, 'user')
        elif choice == '3':
            display_packages(packages, 'critical')
        elif choice == '4':
            display_packages(packages, 'system')
        elif choice == '5':
            interactive_removal(packages)
            break
        elif choice == '6':
            export_requirements(packages)
        elif choice == '7':
            show_docker_instructions()
        elif choice == '8':
            print("Exiting without changes.")
            break
        else:
            print("Invalid choice. Please enter 1-8.")

def export_requirements(packages):
    """Export package list to requirements.txt format."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # All packages
    with open(f'requirements_all_{timestamp}.txt', 'w') as f:
        for pkg in sorted(packages, key=lambda x: x['name'].lower()):
            f.write(f"{pkg['name']}=={pkg['version']}\n")
    
    # User packages only
    user_packages = [p for p in packages if p['is_user_installed'] and not p['is_critical']]
    with open(f'requirements_user_{timestamp}.txt', 'w') as f:
        for pkg in sorted(user_packages, key=lambda x: x['name'].lower()):
            f.write(f"{pkg['name']}=={pkg['version']}\n")
    
    print(f"✅ Requirements files created:")
    print(f"   - requirements_all_{timestamp}.txt (all packages)")
    print(f"   - requirements_user_{timestamp}.txt (user packages only)")

def show_docker_instructions():
    """Show instructions for using Docker for isolated development."""
    print("\n🐳 Docker Development Environment Instructions")
    print("="*50)
    print("To develop in an isolated environment using Docker:")
    print("\n1. Build the development container:")
    print("   docker-compose -f docker-compose.dev.yml build")
    print("\n2. Start the development container:")
    print("   docker-compose -f docker-compose.dev.yml run --rm algo-trading-dev")
    print("\n3. Inside the container, all dependencies will be properly isolated")
    print("   and won't affect your global Python environment.")
    print("\n4. To run the application in the container:")
    print("   docker-compose -f docker-compose.dev.yml up")
    print("\nThis approach ensures all dependencies are installed only in the")
    print("container and not in your global Python environment.")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Please check the error and try again.")