# Python Global Package Cleanup Guide

This guide provides safe commands and procedures for managing globally installed Python packages across different operating systems.

## ⚠️ CRITICAL SAFETY WARNINGS

### Packages That Should NEVER Be Uninstalled
```
pip, setuptools, wheel, distutils, packaging, six
certifi, urllib3, requests, charset-normalizer, idna
python-dateutil, pytz, numpy, scipy
```

### System Package Identification
- Packages starting with: `python3-`, `python-`, `lib`, `system-`
- Packages in system directories: `/usr/lib/python*`, `C:\Python*`, `/Library/Frameworks/Python*`
- OS package manager installed packages (apt, yum, brew, chocolatey)

## 🔍 IMMEDIATE SAFE COMMANDS

### 1. List All Globally Installed Packages

#### Windows:
```cmd
# Basic list
python -m pip list

# Detailed JSON format with locations
python -m pip list --format=json

# Show package locations
python -m pip show <package_name>

# List outdated packages
python -m pip list --outdated
```

#### Linux/Mac:
```bash
# Basic list
python3 -m pip list

# Detailed JSON format
python3 -m pip list --format=json

# Show package locations
python3 -m pip show <package_name>

# List with locations using site module
python3 -c "import site; print('\n'.join(site.getsitepackages()))"
```

### 2. Identify Package Installation Locations

#### Windows:
```cmd
# Show all site-packages directories
python -c "import site; print('\n'.join(site.getsitepackages()))"

# Show user site-packages
python -c "import site; print(site.getusersitepackages())"

# Check specific package location
python -c "import pkg_resources; print(pkg_resources.get_distribution('package_name').location)"
```

#### Linux/Mac:
```bash
# Show all site-packages directories
python3 -c "import site; print('\n'.join(site.getsitepackages()))"

# Show user site-packages
python3 -c "import site; print(site.getusersitepackages())"

# List packages by location
python3 -m pip list -v
```

### 3. Create Backup Before Any Changes

#### Windows:
```cmd
# Create requirements backup
python -m pip freeze > backup_requirements_%date:~-4,4%%date:~-10,2%%date:~-7,2%.txt

# Create detailed JSON backup
python -m pip list --format=json > backup_packages_%date:~-4,4%%date:~-10,2%%date:~-7,2%.json
```

#### Linux/Mac:
```bash
# Create requirements backup
python3 -m pip freeze > backup_requirements_$(date +%Y%m%d).txt

# Create detailed JSON backup
python3 -m pip list --format=json > backup_packages_$(date +%Y%m%d).json
```

## 🛡️ SAFE CLEANUP APPROACHES

### Option 1: Use the Interactive Cleanup Script
```bash
# Run the safe cleanup script
python scripts/cleanup_global_packages.py
```

### Option 2: Manual Selective Cleanup

#### Step 1: Identify User-Installed Packages
```bash
# Windows
python -c "
import subprocess, json, sys
result = subprocess.run([sys.executable, '-m', 'pip', 'list', '--format=json'], capture_output=True, text=True)
packages = json.loads(result.stdout)
user_packages = []
for pkg in packages:
    if pkg['name'].lower() not in ['pip', 'setuptools', 'wheel', 'distutils', 'packaging', 'six', 'certifi', 'urllib3', 'requests']:
        try:
            import pkg_resources
            dist = pkg_resources.get_distribution(pkg['name'])
            if 'users' in dist.location.lower() or 'appdata' in dist.location.lower():
                user_packages.append(pkg['name'])
        except:
            pass
print('User-installed packages:')
for pkg in user_packages:
    print(f'  {pkg}')
"

# Linux/Mac
python3 -c "
import subprocess, json, sys
result = subprocess.run([sys.executable, '-m', 'pip', 'list', '--format=json'], capture_output=True, text=True)
packages = json.loads(result.stdout)
user_packages = []
for pkg in packages:
    if pkg['name'].lower() not in ['pip', 'setuptools', 'wheel', 'distutils', 'packaging', 'six', 'certifi', 'urllib3', 'requests']:
        try:
            import pkg_resources
            dist = pkg_resources.get_distribution(pkg['name'])
            if 'home' in dist.location.lower() or '.local' in dist.location.lower():
                user_packages.append(pkg['name'])
        except:
            pass
print('User-installed packages:')
for pkg in user_packages:
    print(f'  {pkg}')
"
```

#### Step 2: Remove Specific Packages
```bash
# Remove single package
python -m pip uninstall package_name

# Remove multiple packages (review list first!)
python -m pip uninstall package1 package2 package3

# Remove with confirmation
python -m pip uninstall -y package_name
```

### Option 3: Nuclear Option (Use with EXTREME Caution)
```bash
# ⚠️ DANGER: This removes ALL non-critical packages
# Only use if you understand the consequences!

# Windows
python -c "
import subprocess, json, sys
critical = {'pip', 'setuptools', 'wheel', 'distutils', 'packaging', 'six', 'certifi', 'urllib3', 'requests', 'charset-normalizer', 'idna'}
result = subprocess.run([sys.executable, '-m', 'pip', 'list', '--format=json'], capture_output=True, text=True)
packages = [pkg['name'] for pkg in json.loads(result.stdout) if pkg['name'].lower() not in critical]
if packages:
    subprocess.run([sys.executable, '-m', 'pip', 'uninstall'] + packages + ['-y'])
"

# Linux/Mac
python3 -c "
import subprocess, json, sys
critical = {'pip', 'setuptools', 'wheel', 'distutils', 'packaging', 'six', 'certifi', 'urllib3', 'requests', 'charset-normalizer', 'idna'}
result = subprocess.run([sys.executable, '-m', 'pip', 'list', '--format=json'], capture_output=True, text=True)
packages = [pkg['name'] for pkg in json.loads(result.stdout) if pkg['name'].lower() not in critical]
if packages:
    subprocess.run([sys.executable, '-m', 'pip', 'uninstall'] + packages + ['-y'])
"
```

## 🔄 ROLLBACK PROCEDURES

### If Something Goes Wrong

#### 1. Reinstall from Backup
```bash
# Restore from requirements file
python -m pip install -r backup_requirements_YYYYMMDD.txt

# Reinstall critical packages first
python -m pip install --upgrade pip setuptools wheel
```

#### 2. Reinstall Python (Last Resort)
- **Windows**: Download from python.org and reinstall
- **Linux**: Use package manager (`sudo apt install python3-pip`)
- **Mac**: Use Homebrew (`brew install python3`)

#### 3. Virtual Environment Recovery
```bash
# Create new virtual environment
python -m venv recovery_env

# Activate and install essentials
# Windows
recovery_env\Scripts\activate
# Linux/Mac
source recovery_env/bin/activate

pip install --upgrade pip setuptools wheel
```

## 📋 PACKAGE LOCATION GUIDE

### Windows Locations
- **System**: `C:\Python3X\Lib\site-packages\`
- **User**: `C:\Users\<username>\AppData\Roaming\Python\Python3X\site-packages\`
- **Virtual Env**: `<venv_path>\Lib\site-packages\`

### Linux/Mac Locations
- **System**: `/usr/lib/python3.X/site-packages/`
- **User**: `~/.local/lib/python3.X/site-packages/`
- **Homebrew**: `/opt/homebrew/lib/python3.X/site-packages/`
- **Virtual Env**: `<venv_path>/lib/python3.X/site-packages/`

## 🔍 DIAGNOSTIC COMMANDS

### Check Python Installation Health
```bash
# Verify pip works
python -m pip --version

# Check Python paths
python -c "import sys; print('\n'.join(sys.path))"

# Verify critical packages
python -c "import pip, setuptools, wheel; print('Core packages OK')"

# Check for broken packages
python -m pip check
```

### Find Problematic Packages
```bash
# Find packages with missing dependencies
python -m pip check

# Find packages installed in unusual locations
python -c "
import pkg_resources
for dist in pkg_resources.working_set:
    if 'site-packages' not in dist.location:
        print(f'{dist.project_name}: {dist.location}')
"
```

## 🚀 BEST PRACTICES

### 1. Always Use Virtual Environments
```bash
# Create project-specific environments
python -m venv myproject_env
source myproject_env/bin/activate  # Linux/Mac
myproject_env\Scripts\activate     # Windows
```

### 2. Regular Maintenance
```bash
# Weekly package audit
python -m pip list --outdated

# Monthly cleanup check
python scripts/cleanup_global_packages.py
```

### 3. Documentation
- Keep a record of intentionally installed global packages
- Document why each global package is needed
- Regular backup of package states

## 📞 EMERGENCY CONTACTS

If you break your Python installation:

1. **Don't Panic**: Most issues are recoverable
2. **Check Virtual Environments**: Your projects should still work in venvs
3. **Reinstall Python**: Download fresh installer from python.org
4. **Restore from Backup**: Use your requirements.txt files
5. **Ask for Help**: Python community forums, Stack Overflow

## 🎯 QUICK REFERENCE

### Safe Commands to Run Right Now:
```bash
# 1. List all packages
python -m pip list

# 2. Create backup
python -m pip freeze > backup_$(date +%Y%m%d).txt

# 3. Check package health
python -m pip check

# 4. Run interactive cleanup
python scripts/cleanup_global_packages.py
```

### Never Run These Commands:
```bash
# ❌ NEVER DO THIS
pip uninstall pip
pip uninstall setuptools
pip uninstall wheel
rm -rf /usr/lib/python*  # Linux
rmdir /s C:\Python*      # Windows
```

---

**Remember**: When in doubt, create a backup first and test in a virtual environment!