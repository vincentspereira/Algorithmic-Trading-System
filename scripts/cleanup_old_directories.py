#!/usr/bin/env python3
"""
Old Directory Cleanup Script for Nautilus Trader Engine.

This script identifies and removes old directories that are no longer
needed after the project reorganization. It provides safe cleanup
with backup options and validation.

Features:
- Identify obsolete directories
- Safe removal with confirmation
- Backup before deletion
- Validation of removal candidates
- Undo functionality

Usage:
    python scripts/cleanup_old_directories.py [command] [options]

Commands:
    analyze     Analyze directories for cleanup candidates
    cleanup     Remove old directories
    backup      Create backups before cleanup
    restore     Restore from backups
    validate    Validate cleanup safety
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Set, Optional
import argparse
import hashlib

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
BACKUP_DIR = PROJECT_ROOT / "backups" / "old_directories"


class DirectoryCleanupManager:
    """
    Manages cleanup of old directories after project reorganization.

    Provides safe removal of obsolete directories with backup and
    restoration capabilities.
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or PROJECT_ROOT
        self.backup_dir = BACKUP_DIR

        # Directories that should be removed after reorganization
        self.obsolete_directories = {
            # Old structure directories
            'nautilus_trader': 'Replaced by nautilus_trader_engine',
            'analysis/indicators': 'Moved to nautilus_trader_engine/analysis/indicators/',
            'analysis/patterns': 'Moved to nautilus_trader_engine/analysis/patterns/',
            'analysis/market_structure': 'Moved to nautilus_trader_engine/analysis/market_structure/',
            'engines': 'Moved to nautilus_trader_engine/engines/',
            'strategies': 'Moved to nautilus_trader_engine/strategies/',
            'integration': 'Moved to nautilus_trader_engine/integration/',
            'tests': 'Moved to nautilus_trader_engine/tests/',

            # Temporary directories
            'temp': 'Temporary directory',
            'tmp': 'Temporary directory',
            'cache': 'Cache directory',
            'build': 'Build artifacts',
            'dist': 'Distribution artifacts',

            # Old documentation
            'docs - old': 'Old documentation directory',

            # Legacy directories
            'legacy': 'Legacy code directory',
            'deprecated': 'Deprecated code directory',
            'archive': 'Archived code directory',
        }

        # Critical directories that should NEVER be removed
        self.protected_directories = {
            'nautilus_trader_engine',
            'docs',
            'scripts',
            'docker',
            'monitoring',
            'config',
            'infrastructure',
            'k8s',
            'performance',
            'security',
            'validation',
            '.git',
            '.github',
            'backups',
        }

    def analyze_directories(self) -> Dict[str, Any]:
        """
        Analyze project directories for cleanup candidates.

        Returns:
            Analysis results
        """
        analysis = {
            'total_directories': 0,
            'obsolete_candidates': [],
            'protected_directories': [],
            'unknown_directories': [],
            'empty_directories': [],
            'large_directories': []
        }

        # Get all directories in project root
        try:
            items = list(self.project_root.iterdir())
        except PermissionError:
            return {'error': 'Permission denied accessing project root'}

        for item in items:
            if item.is_dir():
                analysis['total_directories'] += 1
                dir_name = item.name

                # Check if directory is protected
                if dir_name in self.protected_directories:
                    analysis['protected_directories'].append({
                        'name': dir_name,
                        'path': str(item),
                        'reason': 'Protected directory'
                    })
                    continue

                # Check if directory is obsolete
                if dir_name in self.obsolete_directories:
                    size_mb = self._get_directory_size(item) / (1024 * 1024)
                    file_count = self._count_files(item)

                    analysis['obsolete_candidates'].append({
                        'name': dir_name,
                        'path': str(item),
                        'reason': self.obsolete_directories[dir_name],
                        'size_mb': round(size_mb, 2),
                        'file_count': file_count,
                        'last_modified': self._get_last_modified(item)
                    })
                    continue

                # Check if directory is empty
                try:
                    if not any(item.iterdir()):
                        analysis['empty_directories'].append({
                            'name': dir_name,
                            'path': str(item)
                        })
                        continue
                except PermissionError:
                    continue

                # Check if directory is large (>100MB)
                size_mb = self._get_directory_size(item) / (1024 * 1024)
                if size_mb > 100:
                    analysis['large_directories'].append({
                        'name': dir_name,
                        'path': str(item),
                        'size_mb': round(size_mb, 2)
                    })
                    continue

                # Unknown directory
                analysis['unknown_directories'].append({
                    'name': dir_name,
                    'path': str(item),
                    'size_mb': round(size_mb, 2)
                })

        return analysis

    def _get_directory_size(self, path: Path) -> int:
        """Get total size of directory in bytes."""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except OSError:
                        continue
        except PermissionError:
            pass
        return total_size

    def _count_files(self, path: Path) -> int:
        """Count total files in directory."""
        count = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                count += len(filenames)
        except PermissionError:
            pass
        return count

    def _get_last_modified(self, path: Path) -> str:
        """Get last modified time of directory."""
        try:
            return datetime.fromtimestamp(path.stat().st_mtime).isoformat()
        except OSError:
            return 'unknown'

    def validate_cleanup_safety(self, directories: List[str]) -> Dict[str, Any]:
        """
        Validate that cleanup of specified directories is safe.

        Args:
            directories: List of directory names to validate

        Returns:
            Validation results
        """
        validation = {
            'safe_to_remove': [],
            'unsafe_to_remove': [],
            'warnings': []
        }

        for dir_name in directories:
            dir_path = self.project_root / dir_name

            if not dir_path.exists():
                validation['warnings'].append(f"Directory {dir_name} does not exist")
                continue

            if dir_name in self.protected_directories:
                validation['unsafe_to_remove'].append({
                    'name': dir_name,
                    'reason': 'Protected directory'
                })
                continue

            # Check for references in codebase
            references = self._find_references_to_directory(dir_name)
            if references:
                validation['unsafe_to_remove'].append({
                    'name': dir_name,
                    'reason': f'Found {len(references)} references in codebase',
                    'references': references[:5]  # Show first 5
                })
                continue

            # Check for recent modifications
            last_modified = self._get_last_modified(dir_path)
            if self._is_recently_modified(last_modified):
                validation['unsafe_to_remove'].append({
                    'name': dir_name,
                    'reason': 'Recently modified',
                    'last_modified': last_modified
                })
                continue

            validation['safe_to_remove'].append({
                'name': dir_name,
                'path': str(dir_path)
            })

        return validation

    def _find_references_to_directory(self, dir_name: str) -> List[str]:
        """Find references to directory in codebase."""
        references = []

        # Search for references in Python files
        for root, dirs, files in os.walk(self.project_root):
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if dir_name in content:
                                references.append(str(file_path.relative_to(self.project_root)))
                    except (UnicodeDecodeError, PermissionError):
                        continue

        return references

    def _is_recently_modified(self, last_modified: str) -> bool:
        """Check if directory was modified recently (within 30 days)."""
        try:
            mod_time = datetime.fromisoformat(last_modified)
            days_since_modified = (datetime.now() - mod_time).days
            return days_since_modified < 30
        except (ValueError, TypeError):
            return False

    def create_backups(self, directories: List[str]) -> Dict[str, Any]:
        """
        Create backups of directories before removal.

        Args:
            directories: List of directory names to backup

        Returns:
            Backup results
        """
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        backup_results = {
            'successful_backups': [],
            'failed_backups': [],
            'total_size_mb': 0
        }

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for dir_name in directories:
            dir_path = self.project_root / dir_name

            if not dir_path.exists():
                backup_results['failed_backups'].append({
                    'name': dir_name,
                    'reason': 'Directory does not exist'
                })
                continue

            # Create backup archive
            backup_name = f"{dir_name}_{timestamp}.tar.gz"
            backup_path = self.backup_dir / backup_name

            try:
                # Create tar.gz archive
                shutil.make_archive(
                    str(backup_path.with_suffix('')),
                    'gztar',
                    str(dir_path)
                )

                size_mb = backup_path.stat().st_size / (1024 * 1024)
                backup_results['successful_backups'].append({
                    'name': dir_name,
                    'backup_path': str(backup_path),
                    'size_mb': round(size_mb, 2)
                })
                backup_results['total_size_mb'] += size_mb

            except Exception as e:
                backup_results['failed_backups'].append({
                    'name': dir_name,
                    'reason': str(e)
                })

        return backup_results

    def cleanup_directories(self, directories: List[str],
                          force: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        """
        Remove specified directories.

        Args:
            directories: List of directory names to remove
            force: Skip safety checks
            dry_run: Show what would be removed without actually removing

        Returns:
            Cleanup results
        """
        cleanup_results = {
            'removed_directories': [],
            'failed_removals': [],
            'skipped_directories': [],
            'total_size_freed_mb': 0
        }

        for dir_name in directories:
            dir_path = self.project_root / dir_name

            if not dir_path.exists():
                cleanup_results['skipped_directories'].append({
                    'name': dir_name,
                    'reason': 'Directory does not exist'
                })
                continue

            # Safety check unless forced
            if not force:
                validation = self.validate_cleanup_safety([dir_name])
                if dir_name in [d['name'] for d in validation['unsafe_to_remove']]:
                    cleanup_results['skipped_directories'].append({
                        'name': dir_name,
                        'reason': 'Safety check failed'
                    })
                    continue

            if dry_run:
                size_mb = self._get_directory_size(dir_path) / (1024 * 1024)
                cleanup_results['removed_directories'].append({
                    'name': dir_name,
                    'path': str(dir_path),
                    'size_mb': round(size_mb, 2),
                    'dry_run': True
                })
                cleanup_results['total_size_freed_mb'] += size_mb
                continue

            try:
                size_mb = self._get_directory_size(dir_path) / (1024 * 1024)

                if dir_path.is_dir():
                    shutil.rmtree(dir_path)
                else:
                    dir_path.unlink()

                cleanup_results['removed_directories'].append({
                    'name': dir_name,
                    'path': str(dir_path),
                    'size_mb': round(size_mb, 2)
                })
                cleanup_results['total_size_freed_mb'] += size_mb

            except Exception as e:
                cleanup_results['failed_removals'].append({
                    'name': dir_name,
                    'reason': str(e)
                })

        return cleanup_results

    def restore_from_backup(self, backup_name: str) -> Dict[str, Any]:
        """
        Restore directory from backup.

        Args:
            backup_name: Name of backup archive

        Returns:
            Restore results
        """
        backup_path = self.backup_dir / backup_name

        if not backup_path.exists():
            return {'error': f'Backup {backup_name} not found'}

        try:
            # Extract archive
            shutil.unpack_archive(str(backup_path), str(self.project_root))

            return {
                'success': True,
                'backup_name': backup_name,
                'restored_path': str(backup_path.with_suffix('').name)
            }

        except Exception as e:
            return {
                'success': False,
                'backup_name': backup_name,
                'error': str(e)
            }

    def generate_cleanup_report(self, analysis: Dict[str, Any]) -> str:
        """Generate a cleanup report."""
        report = []
        report.append("# Directory Cleanup Report")
        report.append("")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")

        report.append("## Summary")
        report.append("")
        report.append(f"- Total directories analyzed: {analysis['total_directories']}")
        report.append(f"- Obsolete candidates: {len(analysis['obsolete_candidates'])}")
        report.append(f"- Protected directories: {len(analysis['protected_directories'])}")
        report.append(f"- Empty directories: {len(analysis['empty_directories'])}")
        report.append(f"- Large directories: {len(analysis['large_directories'])}")
        report.append("")

        if analysis['obsolete_candidates']:
            report.append("## Obsolete Directories")
            report.append("")
            for candidate in analysis['obsolete_candidates']:
                report.append(f"### {candidate['name']}")
                report.append(f"- **Path:** {candidate['path']}")
                report.append(f"- **Reason:** {candidate['reason']}")
                report.append(f"- **Size:** {candidate['size_mb']:.2f} MB")
                report.append(f"- **Files:** {candidate['file_count']}")
                report.append(f"- **Last Modified:** {candidate['last_modified']}")
                report.append("")

        if analysis['empty_directories']:
            report.append("## Empty Directories")
            report.append("")
            for empty in analysis['empty_directories']:
                report.append(f"- `{empty['name']}`: {empty['path']}")
            report.append("")

        if analysis['large_directories']:
            report.append("## Large Directories (>100MB)")
            report.append("")
            for large in analysis['large_directories']:
                report.append(f"- `{large['name']}`: {large['size_mb']:.2f} MB")
            report.append("")

        return "\n".join(report)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Old Directory Cleanup Script for Nautilus Trader Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze directories for cleanup')
    analyze_parser.add_argument('--report', help='Generate report file')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate cleanup safety')
    validate_parser.add_argument('directories', nargs='+', help='Directories to validate')

    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Create backups of directories')
    backup_parser.add_argument('directories', nargs='+', help='Directories to backup')

    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Remove old directories')
    cleanup_parser.add_argument('directories', nargs='+', help='Directories to remove')
    cleanup_parser.add_argument('--force', action='store_true', help='Skip safety checks')
    cleanup_parser.add_argument('--dry-run', action='store_true', help='Show what would be removed')
    cleanup_parser.add_argument('--backup-first', action='store_true', help='Create backups before removal')

    # Restore command
    restore_parser = subparsers.add_parser('restore', help='Restore from backup')
    restore_parser.add_argument('backup_name', help='Name of backup archive to restore')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    manager = DirectoryCleanupManager()

    try:
        if args.command == 'analyze':
            analysis = manager.analyze_directories()

            if 'error' in analysis:
                print(f"Error: {analysis['error']}")
                exit(1)

            # Print summary
            print("Directory Analysis Results:")
            print(f"  Total directories: {analysis['total_directories']}")
            print(f"  Obsolete candidates: {len(analysis['obsolete_candidates'])}")
            print(f"  Protected directories: {len(analysis['protected_directories'])}")
            print(f"  Empty directories: {len(analysis['empty_directories'])}")
            print(f"  Large directories: {len(analysis['large_directories'])}")

            if analysis['obsolete_candidates']:
                print("\nObsolete Candidates:")
                for candidate in analysis['obsolete_candidates']:
                    print(f"  - {candidate['name']}: {candidate['reason']} ({candidate['size_mb']:.2f} MB)")

            # Generate report if requested
            if getattr(args, 'report', None):
                report = manager.generate_cleanup_report(analysis)
                report_file = Path(args.report)
                report_file.write_text(report)
                print(f"\nReport saved to: {report_file}")

        elif args.command == 'validate':
            validation = manager.validate_cleanup_safety(args.directories)

            print("Safety Validation Results:")
            print(f"  Safe to remove: {len(validation['safe_to_remove'])}")
            print(f"  Unsafe to remove: {len(validation['unsafe_to_remove'])}")

            if validation['safe_to_remove']:
                print("\nSafe to remove:")
                for safe in validation['safe_to_remove']:
                    print(f"  ✅ {safe['name']}")

            if validation['unsafe_to_remove']:
                print("\nUnsafe to remove:")
                for unsafe in validation['unsafe_to_remove']:
                    print(f"  ❌ {unsafe['name']}: {unsafe['reason']}")

        elif args.command == 'backup':
            backup_results = manager.create_backups(args.directories)

            print("Backup Results:")
            print(f"  Successful backups: {len(backup_results['successful_backups'])}")
            print(f"  Failed backups: {len(backup_results['failed_backups'])}")
            print(f"  Total size: {backup_results['total_size_mb']:.2f} MB")

            if backup_results['successful_backups']:
                print("\nSuccessful backups:")
                for backup in backup_results['successful_backups']:
                    print(f"  ✅ {backup['name']} -> {backup['backup_path']} ({backup['size_mb']:.2f} MB)")

        elif args.command == 'cleanup':
            directories = args.directories

            # Create backups first if requested
            if getattr(args, 'backup_first', False):
                print("Creating backups...")
                backup_results = manager.create_backups(directories)
                if backup_results['failed_backups']:
                    print("Backup failed, aborting cleanup")
                    exit(1)

            # Perform cleanup
            cleanup_results = manager.cleanup_directories(
                directories,
                force=getattr(args, 'force', False),
                dry_run=getattr(args, 'dry_run', False)
            )

            print("Cleanup Results:")
            if getattr(args, 'dry_run', False):
                print("  DRY RUN - No actual changes made")

            print(f"  Removed directories: {len(cleanup_results['removed_directories'])}")
            print(f"  Failed removals: {len(cleanup_results['failed_removals'])}")
            print(f"  Skipped directories: {len(cleanup_results['skipped_directories'])}")
            print(f"  Space freed: {cleanup_results['total_size_freed_mb']:.2f} MB")

            if cleanup_results['removed_directories']:
                print("\nRemoved directories:")
                for removed in cleanup_results['removed_directories']:
                    dry_run_note = " (dry run)" if removed.get('dry_run') else ""
                    print(f"  ✅ {removed['name']}: {removed['size_mb']:.2f} MB{dry_run_note}")

        elif args.command == 'restore':
            restore_result = manager.restore_from_backup(args.backup_name)

            if restore_result.get('success'):
                print(f"✅ Successfully restored {restore_result['restored_path']} from {args.backup_name}")
            else:
                print(f"❌ Failed to restore: {restore_result.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == '__main__':
    main()