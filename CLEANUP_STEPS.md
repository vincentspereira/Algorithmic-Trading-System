# Python Global Package Cleanup - Quick Reference

## 🚨 SAFETY FIRST
- **ALWAYS** review package lists before removing anything
- **NEVER** remove pip, setuptools, wheel, or other critical packages
- **BACKUP** your package state before making changes
- **TEST** Python functionality after cleanup

## Step-by-Step Cleanup Process

### Step 1: Navigate to Project Directory
```cmd
cd "c:\Users\Vincent_Pereira\Projects\Algo_Trading_Projects\Kilo Code\Algorithmic Trading System"
```

### Step 2: Run Quick Audit (Choose One)
**Option A - Simple Batch Script:**
```cmd
scripts\quick_audit.bat
```

**Option B - Detailed Python Script:**
```cmd
python scripts\quick_package_audit.py
```

### Step 3: Review Results
- Check the package lists displayed
- Identify packages you don't recognize or need
- Note the backup files created
- Look for any dependency issues

### Step 4: Run Interactive Cleanup
```cmd
python scripts\cleanup_global_packages.py
```

### Step 5: Follow Interactive Menu
1. **View packages** - Review what's installed
2. **Select removal method** - All user packages or specific ones
3. **Confirm removal** - Type "yes" to proceed
4. **Verify results** - Check that cleanup was successful

### Step 6: Verify Python Still Works
```cmd
python --version
python -m pip --version
python -c "import sys; print('Python is working!')"
```

### Step 7: Set Up Virtual Environment (After Cleanup)
```cmd
python -m venv venv
venv\Scripts\activate
pip install --upgrade pip
```

## 🛡️ Protected Packages (Never Removed)
- pip, setuptools, wheel
- certifi, urllib3, requests
- packaging, six, distutils
- python-dateutil, pytz
- numpy, scipy (if system-installed)

## 📁 Backup Files Created
- `backup_requirements_YYYYMMDD.txt` - Requirements format
- `backup_packages_YYYYMMDD.json` - Detailed package info
- `backups/python_packages_backup_YYYYMMDD_HHMMSS.json` - Full backup

## 🔧 Troubleshooting

### If Python Stops Working
1. Check if pip is still installed: `python -m pip --version`
2. Reinstall pip if needed: `python -m ensurepip --upgrade`
3. Restore from backup: `pip install -r backup_requirements_YYYYMMDD.txt`

### If Cleanup Script Fails
1. Run as administrator if permission errors occur
2. Close all Python applications and IDEs
3. Use manual removal: `python -m pip uninstall package_name`

### If Virtual Environment Won't Create
1. Ensure Python is working: `python --version`
2. Upgrade pip: `python -m pip install --upgrade pip`
3. Try: `python -m venv --clear venv`

## ⚡ Quick Commands Reference

| Action | Command |
|--------|---------|
| List all packages | `python -m pip list` |
| Check for issues | `python -m pip check` |
| Remove specific package | `python -m pip uninstall package_name` |
| Create virtual environment | `python -m venv venv` |
| Activate virtual environment | `venv\Scripts\activate` |
| Deactivate virtual environment | `deactivate` |

## 🎯 After Cleanup Checklist
- [ ] Python version command works
- [ ] Pip version command works
- [ ] No critical packages were removed
- [ ] Backup files are saved
- [ ] Virtual environment can be created
- [ ] Ready to proceed with Phase 1 setup

---
**Remember:** When in doubt, don't remove it! You can always clean up more packages later.