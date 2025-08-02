#!/usr/bin/env python3
"""
Fix Unicode emoji issues in production readiness framework
Replace emoji characters with ASCII alternatives for Windows compatibility
"""

import re
from pathlib import Path

def fix_unicode_issues():
    """Replace emoji characters with ASCII alternatives"""
    
    framework_file = Path("production_readiness_framework.py")
    
    if not framework_file.exists():
        print("Framework file not found")
        return
    
    # Read the file
    with open(framework_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Define emoji replacements
    replacements = {
        '✅': '[PASS]',
        '❌': '[FAIL]',
        '⚠️': '[WARN]',
        '💥': '[ERROR]',
        '❓': '[UNKNOWN]',
        '⏭️': '[SKIP]',
        '🔥': '[ERROR]',
        '🚨': '[CRITICAL]'
    }
    
    # Apply replacements
    for emoji, replacement in replacements.items():
        content = content.replace(emoji, replacement)
    
    # Write back the file
    with open(framework_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Unicode issues fixed successfully!")

if __name__ == "__main__":
    fix_unicode_issues()