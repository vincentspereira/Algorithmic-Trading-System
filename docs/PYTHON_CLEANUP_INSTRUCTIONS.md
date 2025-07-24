# Python Global Package Cleanup - Detailed Instructions

## Overview

This guide provides comprehensive, step-by-step instructions for safely cleaning up your global Python environment before proceeding with Phase 1 of the Algorithmic Trading System. The cleanup process will remove unnecessary packages while protecting critical system components.

## 🎯 Objectives

- Remove unnecessary globally installed Python packages
- Protect critical system packages from accidental removal
- Create comprehensive backups before any changes
- Verify Python functionality after cleanup
- Prepare for clean virtual environment setup

## 🚨 Important Safety Information

### Critical Packages (Never Remove)
The following packages are essential for Python functionality and will be automatically protected:
- **pip** - Package installer
- **setuptools** - Package building tools
- **wheel** - Binary package format
- **certifi** - SSL certificate bundle
- **urllib3, requests** - HTTP libraries
- **packaging, six, distutils** - Core utilities
- **python-dateutil, pytz** - Date/time handling
- **numpy, scipy** - Mathematical libraries (if system-installed)

### Backup Strategy
The cleanup tools automatically create multiple backup formats:
1. **Requirements format** (`backup_requirements_YYYYMMDD.txt`) - For easy restoration
2. **JSON format** (`backup_packages_YYYYMMDD.json`) - Detailed package information
3. **Full backup** (`backups/python_packages_backup_YYYYMMDD_HHMMSS.json`) - Complete system state

## 📋 Prerequisites

1. **Administrative Access**: You may need administrator privileges for some operations
2. **Close Applications**: Close all Python applications, IDEs, and terminals
3. **Stable Internet**: Required for package operations
4. **Backup Space**: Ensure sufficient disk space for backups

## 🔧 Step-by-Step Instructions

### Step 1: Open Command Prompt as Administrator

1. Press `Win + R` to open Run dialog
2. Type `cmd` and press `Ctrl + Shift + Enter` (opens as administrator)
3. Click "Yes" when prompted by User Account Control

### Step 2: Navigate to Project Directory

```cmd
cd "c:\Users\Vincent_Pereira\Projects\Algo_Trading_Projects\Kilo Code\Algorithmic Trading System"
```

**Verify you're in the correct directory:**
```cmd
dir
```
You should see files like `README.md`, `docker-compose.yml`, and the `scripts` folder.

### Step 3: Run the Quick Audit

You have two options for the initial audit:

#### Option A: Simple Batch Script (Recommended for beginners)

```cmd
scripts\quick_audit.bat
```

**What this does:**
- Creates a backup directory
- Generates a requirements backup file
- Lists all installed packages
- Shows outdated packages
- Checks for dependency issues
- Displays Python installation information

**Expected output:**
- Package lists will be displayed on screen
- A backup file will be created in the `backups` folder
- The script will pause at the end for you to review

#### Option B: Detailed Python Script (More comprehensive)

```cmd
python scripts\quick_package_audit.py
```

**What this does:**
- Shows detailed Python installation information
- Creates both requirements and JSON backups
- Analyzes packages by category (critical, user, system)
- Provides detailed package analysis
- Shows next steps recommendations

### Step 4: Review the Audit Results

**Look for the following information:**

1. **Total Package Count**: How many packages are installed
2. **Critical Packages**: Protected packages that won't be removed
3. **User Packages**: Packages safe for removal
4. **Outdated Packages**: Packages that could be updated
5. **Dependency Issues**: Any broken package dependencies

**Red Flags to Watch For:**
- Packages you don't recognize
- Packages with unusual names or versions
- Dependency conflicts reported by `pip check`

### Step 5: Run the Interactive Cleanup Tool

```cmd
python scripts\cleanup_global_packages.py
```

**What happens when you run this:**

1. **System Scan**: The script scans all installed packages
2. **Backup Creation**: Automatic backup of current state
3. **Package Analysis**: Categorizes packages by safety level
4. **Interactive Menu**: Presents options for cleanup

### Step 6: Navigate the Interactive Menu

The cleanup tool presents a menu with these options:

```
1. View all packages
2. View user packages only
3. View critical packages (protected)
4. View system packages
5. Start interactive removal
6. Export package list to requirements.txt
7. Exit
```

**Recommended workflow:**

1. **First, choose option 2** - "View user packages only"
   - This shows packages that are safe to remove
   - Review the list carefully
   - Note any packages you recognize and want to keep

2. **Then choose option 3** - "View critical packages (protected)"
   - Verify that essential packages are protected
   - These will never be removed

3. **Choose option 5** - "Start interactive removal"
   - This begins the actual cleanup process

### Step 7: Interactive Package Removal

When you select "Start interactive removal", you'll see:

```
Options:
1. Remove all user packages
2. Select specific packages to remove
3. Show package details
4. Exit without changes
```

**For most users, we recommend option 2** - "Select specific packages to remove"

#### Selecting Specific Packages

1. The script will display numbered packages
2. You can select packages using:
   - Individual numbers: `1,3,5`
   - Ranges: `1-5,8-10`
   - All: `all`
   - None: `none` or just press Enter

3. **Example selection:**
   ```
   Selection: 1,3,5-8,12
   ```

4. **Confirm your selection:**
   - The script will show selected packages
   - Type `yes` to proceed or `no` to cancel

### Step 8: Monitor the Removal Process

During removal, you'll see:
```
🗑️  Removing 5 packages...
Removing package1...
✅ Successfully removed package1
Removing package2...
✅ Successfully removed package2
...
✅ Package removal completed.
```

**If errors occur:**
- Note which packages failed to remove
- These might be in use or have dependencies
- You can try removing them manually later

### Step 9: Verify Python Functionality

After cleanup, verify everything still works:

```cmd
python --version
```
**Expected output:** `Python 3.x.x`

```cmd
python -m pip --version
```
**Expected output:** `pip x.x.x from ...`

```cmd
python -c "import sys; print('Python is working correctly!')"
```
**Expected output:** `Python is working correctly!`

```cmd
python -m pip check
```
**Expected output:** No errors or warnings

### Step 10: Final Verification

Run a final package list to see the results:

```cmd
python -m pip list
```

**What to look for:**
- Significantly fewer packages than before
- All critical packages still present
- No obvious missing dependencies

## 🔄 Post-Cleanup Steps

### Create a Clean Virtual Environment

Now that your global environment is clean, create a virtual environment for the project:

```cmd
python -m venv venv
```

**Activate the virtual environment:**
```cmd
venv\Scripts\activate
```

**Upgrade pip in the virtual environment:**
```cmd
pip install --upgrade pip
```

**Verify the virtual environment:**
```cmd
pip list
```
You should see only a few basic packages (pip, setuptools, wheel).

### Prepare for Phase 1

With a clean environment, you're ready to proceed with Phase 1 setup:

```cmd
scripts\setup_dev_env.bat
```

## 🚨 Troubleshooting

### Problem: "Permission Denied" Errors

**Solution:**
1. Close all Python applications and IDEs
2. Run Command Prompt as Administrator
3. Try the cleanup again

### Problem: Python Command Not Found

**Solution:**
1. Check if Python is in your PATH:
   ```cmd
   where python
   ```
2. If not found, reinstall Python or add to PATH
3. Use full path: `C:\Python3x\python.exe`

### Problem: Pip Not Working After Cleanup

**Solution:**
1. Reinstall pip:
   ```cmd
   python -m ensurepip --upgrade
   ```
2. Or download get-pip.py and run:
   ```cmd
   python get-pip.py
   ```

### Problem: Critical Package Accidentally Removed

**Solution:**
1. Restore from backup:
   ```cmd
   pip install -r backups\backup_requirements_YYYYMMDD.txt
   ```
2. Or reinstall specific packages:
   ```cmd
   pip install pip setuptools wheel
   ```

### Problem: Virtual Environment Won't Create

**Solution:**
1. Ensure Python is working:
   ```cmd
   python --version
   ```
2. Try with full path:
   ```cmd
   python -m venv --clear venv
   ```
3. Check for antivirus interference

## 📊 Expected Results

After successful cleanup, you should have:

- **Reduced package count**: From potentially 100+ packages to 20-30 essential ones
- **Clean global environment**: Only critical and necessary packages
- **Working Python**: All basic functionality intact
- **Backup files**: Complete restoration capability
- **Ready for Phase 1**: Clean slate for project-specific installations

## 🎯 Success Indicators

✅ **Python version command works**
✅ **Pip version command works**  
✅ **No critical packages removed**
✅ **Backup files created and saved**
✅ **Virtual environment creates successfully**
✅ **No dependency conflicts**
✅ **Significantly fewer global packages**

## 📞 Getting Help

If you encounter issues:

1. **Check the backup files** - They're your safety net
2. **Review error messages** - They often contain the solution
3. **Try manual removal** - For stubborn packages: `pip uninstall package_name`
4. **Restore from backup** - If something goes wrong: `pip install -r backup_file.txt`

## 🔄 Next Steps

Once cleanup is complete:

1. **Verify all checks pass** ✅
2. **Create and test virtual environment** ✅
3. **Proceed with Phase 1 setup** ✅
4. **Run Phase 1 validation** ✅

---

**Remember**: This cleanup is a one-time process that will make your Python development environment much cleaner and more manageable. Take your time, read the output carefully, and don't hesitate to exit without changes if you're unsure about anything.