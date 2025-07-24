# Python Package Cleanup - Immediate Commands

## 🚀 COMMANDS YOU CAN RUN RIGHT NOW

### Windows Users:
```cmd
# Quick audit (automated)
scripts\quick_audit.bat

# Or run individual commands:
python -m pip list
python -m pip freeze > backup_requirements.txt
python -m pip check
python scripts\quick_package_audit.py
python scripts\cleanup_global_packages.py
```

### Linux/Mac Users:
```bash
# Make script executable first
chmod +x scripts/quick_audit.sh

# Quick audit (automated)
./scripts/quick_audit.sh

# Or run individual commands:
python3 -m pip list
python3 -m pip freeze > backup_requirements.txt
python3 -m pip check
python3 scripts/quick_package_audit.py
python3 scripts/cleanup_global_packages.py
```

## 📋 WHAT EACH SCRIPT DOES

### 1. `quick_audit.bat` / `quick_audit.sh`
- **Purpose**: Immediate safety audit
- **Actions**: 
  - Creates automatic backup
  - Lists all packages
  - Shows outdated packages
  - Checks dependencies
  - Shows Python info
- **Safe**: ✅ Read-only, no changes made

### 2. `scripts/quick_package_audit.py`
- **Purpose**: Detailed analysis with Python
- **Actions**:
  - Comprehensive package analysis
  - Identifies critical vs user packages
  - Creates JSON and requirements backups
  - Shows installation paths
- **Safe**: ✅ Read-only, creates backups

### 3. `scripts/cleanup_global_packages.py`
- **Purpose**: Interactive cleanup tool
- **Actions**:
  - Safe package removal with protection
  - Interactive selection
  - Automatic backups before changes
  - Excludes critical packages
- **Safe**: ⚠️ Makes changes, but with safety checks

## 🛡️ CRITICAL PACKAGES (NEVER REMOVE)
```
pip, setuptools, wheel, distutils, packaging, six
certifi, urllib3, requests, charset-normalizer, idna
python-dateutil, pytz, numpy, scipy
```

## 📁 FILES CREATED

### Scripts:
- `scripts/cleanup_global_packages.py` - Main interactive cleanup tool
- `scripts/quick_package_audit.py` - Detailed Python analysis
- `scripts/quick_audit.bat` - Windows quick commands
- `scripts/quick_audit.sh` - Linux/Mac quick commands

### Documentation:
- `docs/PYTHON_GLOBAL_PACKAGE_CLEANUP.md` - Complete guide
- `PYTHON_PACKAGE_CLEANUP_SUMMARY.md` - This summary

## 🎯 RECOMMENDED WORKFLOW

### Step 1: Immediate Safety Check
```bash
# Windows
scripts\quick_audit.bat

# Linux/Mac
chmod +x scripts/quick_audit.sh && ./scripts/quick_audit.sh
```

### Step 2: Detailed Analysis
```bash
# Windows
python scripts\quick_package_audit.py

# Linux/Mac
python3 scripts/quick_package_audit.py
```

### Step 3: Safe Cleanup (if needed)
```bash
# Windows
python scripts\cleanup_global_packages.py

# Linux/Mac
python3 scripts/cleanup_global_packages.py
```

## ⚠️ SAFETY REMINDERS

1. **Always backup first** - All scripts create backups automatically
2. **Review before removing** - Never blindly remove packages
3. **Test critical functionality** - Verify Python still works after cleanup
4. **Use virtual environments** - Avoid global installs in the future
5. **Keep emergency contacts** - Know how to reinstall Python if needed

## 🔄 ROLLBACK COMMANDS

If something goes wrong:
```bash
# Reinstall from backup
python -m pip install -r backup_requirements_YYYYMMDD.txt

# Reinstall critical packages
python -m pip install --upgrade pip setuptools wheel

# Check Python health
python -m pip check
python -c "import pip, setuptools, wheel; print('Core packages OK')"
```

## 📞 EMERGENCY RECOVERY

If Python breaks completely:
1. **Don't panic** - Virtual environments should still work
2. **Reinstall Python** - Download from python.org
3. **Restore from backup** - Use your requirements.txt files
4. **Verify installation** - Run `python -m pip --version`

---

**Start with the quick audit commands above to safely assess your current state!**