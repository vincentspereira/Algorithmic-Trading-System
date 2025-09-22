#!/usr/bin/env python3
"""
Semantic Version Manager for Nautilus Trader Engine.

This script implements semantic versioning (SemVer) with automated version
bumping, changelog generation, and release management for the trading system.

Features:
- Automated version calculation from commits
- Conventional commit parsing
- Release branch management
- Version tagging and GitHub releases
- Changelog generation
- Pre-release and build metadata support

Usage:
    python scripts/version_manager.py [command] [options]

Commands:
    current     Show current version
    bump        Bump version based on commits
    release     Create a new release
    changelog  Generate changelog
    validate   Validate version format
"""

import os
import re
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import semver

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
VERSION_FILE = PROJECT_ROOT / "VERSION"
CHANGELOG_FILE = PROJECT_ROOT / "CHANGELOG.md"


class SemanticVersionManager:
    """
    Manages semantic versioning for the Nautilus Trader Engine.

    Implements SemVer 2.0.0 with conventional commit parsing and
    automated version management.
    """

    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path or PROJECT_ROOT
        self.version_file = VERSION_FILE
        self.changelog_file = CHANGELOG_FILE

    def get_current_version(self) -> str:
        """Get the current version from VERSION file or git tags."""
        # Try VERSION file first
        if self.version_file.exists():
            version = self.version_file.read_text().strip()
            if self._is_valid_semver(version):
                return version

        # Fall back to git tags
        try:
            result = subprocess.run(
                ['git', 'describe', '--tags', '--abbrev=0'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            version = result.stdout.strip()
            if version.startswith('v'):
                version = version[1:]
            if self._is_valid_semver(version):
                return version
        except subprocess.CalledProcessError:
            pass

        # Default to 0.1.0 for new projects
        return "0.1.0"

    def bump_version(self, bump_type: Optional[str] = None,
                    pre_release: Optional[str] = None,
                    build_metadata: Optional[str] = None) -> str:
        """
        Bump version based on conventional commits or specified type.

        Args:
            bump_type: 'major', 'minor', 'patch', or None for auto-detection
            pre_release: Pre-release identifier (alpha, beta, rc)
            build_metadata: Build metadata

        Returns:
            New version string
        """
        current_version = self.get_current_version()

        if bump_type:
            # Manual bump
            new_version = self._bump_manual(current_version, bump_type)
        else:
            # Auto-detect from commits
            new_version = self._bump_auto(current_version)

        # Add pre-release and build metadata
        if pre_release:
            new_version = f"{new_version}-{pre_release}"

        if build_metadata:
            new_version = f"{new_version}+{build_metadata}"

        # Validate the new version
        if not self._is_valid_semver(new_version):
            raise ValueError(f"Invalid version format: {new_version}")

        return new_version

    def _bump_manual(self, current_version: str, bump_type: str) -> str:
        """Manually bump version by type."""
        version = semver.VersionInfo.parse(current_version)

        if bump_type == 'major':
            return str(version.bump_major())
        elif bump_type == 'minor':
            return str(version.bump_minor())
        elif bump_type == 'patch':
            return str(version.bump_patch())
        else:
            raise ValueError(f"Invalid bump type: {bump_type}")

    def _bump_auto(self, current_version: str) -> str:
        """Automatically bump version based on conventional commits."""
        # Get commits since last tag
        commits = self._get_commits_since_last_tag()

        # Analyze commit types
        has_breaking = any(self._is_breaking_commit(commit) for commit in commits)
        has_features = any(commit['type'] == 'feat' for commit in commits)
        has_fixes = any(commit['type'] == 'fix' for commit in commits)

        version = semver.VersionInfo.parse(current_version)

        if has_breaking:
            return str(version.bump_major())
        elif has_features:
            return str(version.bump_minor())
        elif has_fixes:
            return str(version.bump_patch())
        else:
            # No changes requiring version bump
            return current_version

    def _get_commits_since_last_tag(self) -> List[Dict[str, Any]]:
        """Get commits since the last tag."""
        try:
            # Get the last tag
            result = subprocess.run(
                ['git', 'describe', '--tags', '--abbrev=0'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            last_tag = result.stdout.strip()

            # Get commits since last tag
            result = subprocess.run(
                ['git', 'log', '--pretty=format:%H|%s|%D', f'{last_tag}..HEAD'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )

            commits = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split('|', 2)
                    if len(parts) >= 2:
                        commit_hash, subject, refs = parts if len(parts) > 2 else parts + ['']

                        commit_type = self._parse_commit_type(subject)
                        commits.append({
                            'hash': commit_hash,
                            'subject': subject,
                            'type': commit_type,
                            'breaking': self._is_breaking_commit({'subject': subject, 'type': commit_type})
                        })

            return commits

        except subprocess.CalledProcessError:
            # No previous tags, get all commits
            return []

    def _parse_commit_type(self, subject: str) -> str:
        """Parse conventional commit type from subject."""
        # Conventional commit format: type(scope): description
        match = re.match(r'^(\w+)(\([^)]+\))?:', subject.strip())
        if match:
            return match.group(1)
        return 'other'

    def _is_breaking_commit(self, commit: Dict[str, Any]) -> bool:
        """Check if commit introduces breaking changes."""
        subject = commit['subject'].lower()

        # Check for BREAKING CHANGE in footer
        if 'breaking change' in subject or 'breaking-change' in subject:
            return True

        # Check for ! after type (conventional commit breaking change indicator)
        if re.search(r'^\w+!:|^\w+\([^)]+\)!:', commit['subject']):
            return True

        # Check for major version changes in commit messages
        if any(keyword in subject for keyword in [
            'breaking', 'incompatible', 'api change', 'removes', 'deletes'
        ]):
            return True

        return False

    def create_release(self, version: str, create_tag: bool = True,
                      push_changes: bool = False) -> bool:
        """
        Create a new release with version bump and changelog.

        Args:
            version: Version to release
            create_tag: Whether to create git tag
            push_changes: Whether to push changes to remote

        Returns:
            Success status
        """
        print(f"Creating release {version}...")

        try:
            # Update VERSION file
            self.version_file.write_text(version)
            print(f"✓ Updated VERSION file to {version}")

            # Generate changelog
            changelog = self.generate_changelog(version)
            if changelog:
                self._update_changelog_file(changelog)
                print("✓ Updated CHANGELOG.md")

            # Commit changes
            subprocess.run(
                ['git', 'add', 'VERSION', 'CHANGELOG.md'],
                cwd=self.repo_path,
                check=True
            )

            subprocess.run(
                ['git', 'commit', '-m', f"chore: release {version}"],
                cwd=self.repo_path,
                check=True
            )
            print("✓ Committed version changes")

            if create_tag:
                # Create annotated tag
                subprocess.run(
                    ['git', 'tag', '-a', f"v{version}", '-m', f"Release {version}"],
                    cwd=self.repo_path,
                    check=True
                )
                print(f"✓ Created git tag v{version}")

            if push_changes:
                # Push commits and tags
                subprocess.run(
                    ['git', 'push', 'origin', 'main'],
                    cwd=self.repo_path,
                    check=True
                )

                subprocess.run(
                    ['git', 'push', 'origin', f"v{version}"],
                    cwd=self.repo_path,
                    check=True
                )
                print("✓ Pushed changes and tags to remote")

            print(f"🎉 Release {version} created successfully!")
            return True

        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create release: {e}")
            return False

    def generate_changelog(self, version: str,
                          previous_version: Optional[str] = None) -> str:
        """
        Generate changelog for the specified version.

        Args:
            version: Version to generate changelog for
            previous_version: Previous version for comparison

        Returns:
            Formatted changelog
        """
        if not previous_version:
            previous_version = self.get_current_version()

        # Get commits between versions
        commits = self._get_commits_between_versions(previous_version, version)

        if not commits:
            return ""

        # Categorize commits
        categorized = self._categorize_commits(commits)

        # Generate markdown
        return self._format_changelog_markdown(version, categorized, commits)

    def _get_commits_between_versions(self, from_version: str, to_version: str) -> List[Dict[str, Any]]:
        """Get commits between two versions."""
        try:
            from_ref = f"v{from_version}" if not from_version.startswith('v') else from_version
            to_ref = f"v{to_version}" if not to_version.startswith('v') else to_version

            result = subprocess.run(
                ['git', 'log', '--pretty=format:%H|%an|%ae|%s|%D', f'{from_ref}..{to_ref}'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )

            commits = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split('|', 4)
                    if len(parts) >= 4:
                        commit_hash, author, email, subject, refs = parts if len(parts) > 4 else parts + ['']

                        commits.append({
                            'hash': commit_hash,
                            'author': author,
                            'email': email,
                            'subject': subject,
                            'type': self._parse_commit_type(subject),
                            'scope': self._parse_commit_scope(subject),
                            'breaking': self._is_breaking_commit({'subject': subject, 'type': self._parse_commit_type(subject)})
                        })

            return commits

        except subprocess.CalledProcessError:
            return []

    def _parse_commit_scope(self, subject: str) -> Optional[str]:
        """Parse conventional commit scope."""
        match = re.match(r'^\w+\(([^)]+)\):', subject.strip())
        return match.group(1) if match else None

    def _categorize_commits(self, commits: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize commits by type."""
        categories = {
            'breaking': [],
            'features': [],
            'fixes': [],
            'documentation': [],
            'performance': [],
            'refactoring': [],
            'testing': [],
            'ci': [],
            'other': []
        }

        for commit in commits:
            if commit['breaking']:
                categories['breaking'].append(commit)
            elif commit['type'] == 'feat':
                categories['features'].append(commit)
            elif commit['type'] == 'fix':
                categories['fixes'].append(commit)
            elif commit['type'] == 'docs':
                categories['documentation'].append(commit)
            elif commit['type'] == 'perf':
                categories['performance'].append(commit)
            elif commit['type'] == 'refactor':
                categories['refactoring'].append(commit)
            elif commit['type'] == 'test':
                categories['testing'].append(commit)
            elif commit['type'] == 'ci':
                categories['ci'].append(commit)
            else:
                categories['other'].append(commit)

        return categories

    def _format_changelog_markdown(self, version: str,
                                  categorized: Dict[str, List[Dict[str, Any]]],
                                  all_commits: List[Dict[str, Any]]) -> str:
        """Format changelog as markdown."""
        lines = []

        # Header
        lines.append(f"## [{version}] - {datetime.now().strftime('%Y-%m-%d')}")
        lines.append("")

        # Categories
        category_names = {
            'breaking': '### ⚠️ Breaking Changes',
            'features': '### ✨ New Features',
            'fixes': '### 🐛 Bug Fixes',
            'documentation': '### 📚 Documentation',
            'performance': '### ⚡ Performance Improvements',
            'refactoring': '### 🔄 Code Refactoring',
            'testing': '### 🧪 Testing',
            'ci': '### 🤖 CI/CD',
            'other': '### 📝 Other Changes'
        }

        for category, commits in categorized.items():
            if commits:
                lines.append(category_names[category])
                lines.append("")

                for commit in commits:
                    scope = f"**{commit['scope']}**: " if commit.get('scope') else ""
                    subject = self._clean_commit_subject(commit['subject'])
                    author = f" (by {commit['author']})"
                    lines.append(f"- {scope}{subject}{author}")

                lines.append("")

        # Contributors
        contributors = set(commit['author'] for commit in all_commits)
        if contributors:
            lines.append("### 👥 Contributors")
            lines.append("")
            lines.append(", ".join(sorted(contributors)))
            lines.append("")

        return "\n".join(lines)

    def _clean_commit_subject(self, subject: str) -> str:
        """Clean commit subject for changelog."""
        # Remove conventional commit prefix
        subject = re.sub(r'^\w+(\([^)]+\))?:', '', subject).strip()

        # Capitalize first letter
        if subject:
            subject = subject[0].upper() + subject[1:]

        return subject

    def _update_changelog_file(self, new_entry: str):
        """Update CHANGELOG.md with new entry."""
        if not self.changelog_file.exists():
            # Create new changelog
            content = "# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n"
            content += "The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),\n"
            content += "and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).\n\n"
        else:
            content = self.changelog_file.read_text()

        # Insert new entry after header
        lines = content.split('\n')
        insert_index = 0
        for i, line in enumerate(lines):
            if line.startswith('## ['):
                insert_index = i
                break

        lines.insert(insert_index, new_entry)

        self.changelog_file.write_text('\n'.join(lines))

    def validate_version(self, version: str) -> bool:
        """Validate version format."""
        return self._is_valid_semver(version)

    def _is_valid_semver(self, version: str) -> bool:
        """Check if version is valid SemVer."""
        try:
            semver.VersionInfo.parse(version)
            return True
        except ValueError:
            return False

    def get_version_info(self, version: str) -> Dict[str, Any]:
        """Get detailed version information."""
        if not self._is_valid_semver(version):
            raise ValueError(f"Invalid version: {version}")

        parsed = semver.VersionInfo.parse(version)

        return {
            'major': parsed.major,
            'minor': parsed.minor,
            'patch': parsed.patch,
            'prerelease': parsed.prerelease,
            'build': parsed.build,
            'string': str(parsed)
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Semantic Version Manager for Nautilus Trader Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Current version command
    subparsers.add_parser('current', help='Show current version')

    # Bump version command
    bump_parser = subparsers.add_parser('bump', help='Bump version')
    bump_parser.add_argument('--type', choices=['major', 'minor', 'patch'],
                           help='Version bump type (auto-detected if not specified)')
    bump_parser.add_argument('--pre-release', help='Pre-release identifier')
    bump_parser.add_argument('--build', help='Build metadata')
    bump_parser.add_argument('--dry-run', action='store_true', help='Show what would be done')

    # Release command
    release_parser = subparsers.add_parser('release', help='Create a new release')
    release_parser.add_argument('--version', help='Version to release')
    release_parser.add_argument('--no-tag', action='store_true', help='Do not create git tag')
    release_parser.add_argument('--no-push', action='store_true', help='Do not push changes')

    # Changelog command
    changelog_parser = subparsers.add_parser('changelog', help='Generate changelog')
    changelog_parser.add_argument('--version', required=True, help='Version for changelog')
    changelog_parser.add_argument('--previous', help='Previous version')
    changelog_parser.add_argument('--output', '-o', help='Output file')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate version format')
    validate_parser.add_argument('version', help='Version to validate')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    manager = SemanticVersionManager()

    try:
        if args.command == 'current':
            version = manager.get_current_version()
            print(f"Current version: {version}")

        elif args.command == 'bump':
            new_version = manager.bump_version(
                bump_type=getattr(args, 'type', None),
                pre_release=getattr(args, 'pre_release', None),
                build_metadata=getattr(args, 'build', None)
            )

            if getattr(args, 'dry_run', False):
                current = manager.get_current_version()
                print(f"Current version: {current}")
                print(f"New version would be: {new_version}")
            else:
                print(f"Version bumped to: {new_version}")
                manager.version_file.write_text(new_version)

        elif args.command == 'release':
            version = getattr(args, 'version', None)
            if not version:
                # Auto-bump for release
                version = manager.bump_version()

            success = manager.create_release(
                version=version,
                create_tag=not getattr(args, 'no_tag', False),
                push_changes=not getattr(args, 'no_push', False)
            )

            if success:
                print(f"✅ Release {version} created successfully!")
            else:
                print("❌ Release creation failed!")
                exit(1)

        elif args.command == 'changelog':
            changelog = manager.generate_changelog(
                version=args.version,
                previous_version=getattr(args, 'previous', None)
            )

            if getattr(args, 'output', None):
                Path(args.output).write_text(changelog)
                print(f"Changelog written to {args.output}")
            else:
                print(changelog)

        elif args.command == 'validate':
            if manager.validate_version(args.version):
                print(f"✅ {args.version} is a valid SemVer version")
                info = manager.get_version_info(args.version)
                print(f"   Major: {info['major']}")
                print(f"   Minor: {info['minor']}")
                print(f"   Patch: {info['patch']}")
                if info['prerelease']:
                    print(f"   Pre-release: {info['prerelease']}")
                if info['build']:
                    print(f"   Build: {info['build']}")
            else:
                print(f"❌ {args.version} is not a valid SemVer version")
                exit(1)

    except Exception as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == '__main__':
    main()