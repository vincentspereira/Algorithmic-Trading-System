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
```

## Python Package Management

This guide provides immediate commands and tools for managing and cleaning up Python packages in your development environment.

## Key Features

- **Immediate Commands** - Ready-to-run cleanup commands
- **Cross-Platform Support** - Instructions for Windows, Linux, and Mac
- **Automated Scripts** - One-command cleanup process
- **Safety Features** - Backup creation before cleanup

These tools help maintain a clean Python environment and resolve package conflicts efficiently.