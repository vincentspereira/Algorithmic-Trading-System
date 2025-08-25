#!/usr/bin/env python3

import json
import shutil
from datetime import datetime
import os
from pathlib import Path

def backup_configuration():
    """Create timestamped backups of critical configuration files"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    
    # Backup dependencies.json
    try:
        deps_file = Path("dependency_management/dependencies.json")
        if deps_file.exists():
            backup_path = backup_dir / f"dependencies_{timestamp}.json"
            shutil.copy2(deps_file, backup_path)
            print(f"Dependencies configuration backed up to {backup_path}")
    except Exception as e:
        print(f"Error backing up dependencies.json: {e}")
    
    # Backup monitoring configurations
    try:
        workflows_dir = Path(".github/workflows")
        if workflows_dir.exists():
            backup_path = backup_dir / f"workflows_{timestamp}"
            backup_path.mkdir(exist_ok=True)
            shutil.copytree(workflows_dir, backup_path, dirs_exist_ok=True)
            print(f"Workflows backed up to {backup_path}")
    except Exception as e:
        print(f"Error backing up workflows: {e}")
    
    # Backup scripts
    try:
        scripts_dir = Path("scripts")
        if scripts_dir.exists():
            backup_path = backup_dir / f"scripts_{timestamp}"
            backup_path.mkdir(exist_ok=True)
            shutil.copytree(scripts_dir, backup_path, dirs_exist_ok=True)
            print(f"Scripts backed up to {backup_path}")
    except Exception as e:
        print(f"Error backing up scripts: {e}")
    
    # Cleanup old backups (keep last 5)
    cleanup_old_backups()

def cleanup_old_backups():
    """Keep only the 5 most recent backups of each type"""
    backup_dir = Path("backups")
    if not backup_dir.exists():
        return
    
    # Group files by type
    backup_types = {
        "dependencies": [],
        "workflows": [],
        "scripts": []
    }
    
    for item in backup_dir.iterdir():
        if item.name.startswith("dependencies_"):
            backup_types["dependencies"].append(item)
        elif item.name.startswith("workflows_"):
            backup_types["workflows"].append(item)
        elif item.name.startswith("scripts_"):
            backup_types["scripts"].append(item)
    
    # Keep only the 5 most recent for each type
    for type_files in backup_types.values():
        if len(type_files) > 5:
            sorted_files = sorted(type_files, key=lambda x: x.stat().st_mtime, reverse=True)
            for old_file in sorted_files[5:]:
                if old_file.is_dir():
                    shutil.rmtree(old_file)
                else:
                    old_file.unlink()

if __name__ == "__main__":
    backup_configuration()
