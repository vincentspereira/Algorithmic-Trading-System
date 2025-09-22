#!/usr/bin/env python3
"""
Documentation Reference Updater for Nautilus Trader Engine.

This script updates all documentation references throughout the codebase
to reflect the new project structure, renamed files, and updated paths.

Features:
- Update file path references in documentation
- Fix broken links and cross-references
- Update import statements in documentation
- Validate documentation integrity
- Generate documentation index

Usage:
    python scripts/update_docs_references.py [command] [options]

Commands:
    update     Update documentation references
    validate   Validate documentation references
    index      Generate documentation index
    fix-links  Fix broken links in documentation
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple, Optional
from collections import defaultdict
import argparse

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
NAUTILUS_PACKAGE = PROJECT_ROOT / "nautilus_trader_engine"


class DocumentationReferenceUpdater:
    """
    Updates documentation references throughout the codebase.

    Handles path updates, link fixes, and reference validation
    for comprehensive documentation maintenance.
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or PROJECT_ROOT
        self.docs_dir = DOCS_DIR
        self.nautilus_package = NAUTILUS_PACKAGE

        # Path mapping for renamed/moved files
        self.path_mappings = {
            # Old path -> New path mappings
            'nautilus_trader/': 'nautilus_trader_engine/',
            'analysis/indicators/': 'nautilus_trader_engine/analysis/indicators/',
            'analysis/patterns/': 'nautilus_trader_engine/analysis/patterns/',
            'analysis/market_structure/': 'nautilus_trader_engine/analysis/market_structure/',
            'engines/': 'nautilus_trader_engine/engines/',
            'strategies/': 'nautilus_trader_engine/strategies/',
            'integration/': 'nautilus_trader_engine/integration/',
            'tests/': 'nautilus_trader_engine/tests/',
        }

        # File extension mappings
        self.file_mappings = {
            # Old filename -> New filename mappings
            'README.md': 'docs/README.md',
            'INDICATORS_REFERENCE.md': 'docs/INDICATORS_REFERENCE.md',
            'API_DOCUMENTATION.md': 'docs/api/README.md',
        }

    def discover_documentation_files(self) -> List[Path]:
        """Discover all documentation files."""
        doc_files = []

        # Common documentation extensions
        doc_extensions = {'.md', '.rst', '.txt', '.adoc', '.asciidoc'}

        # Search in docs directory
        if self.docs_dir.exists():
            for root, dirs, files in os.walk(self.docs_dir):
                for file in files:
                    if any(file.endswith(ext) for ext in doc_extensions):
                        doc_files.append(Path(root) / file)

        # Also search for documentation in source code (docstrings, comments)
        for root, dirs, files in os.walk(self.nautilus_package):
            for file in files:
                if file.endswith('.py'):
                    doc_files.append(Path(root) / file)

        return doc_files

    def update_references(self, files: Optional[List[Path]] = None,
                         dry_run: bool = False) -> Dict[str, Any]:
        """
        Update documentation references.

        Args:
            files: Specific files to update (None for all)
            dry_run: Show changes without applying them

        Returns:
            Update summary
        """
        if files is None:
            files = self.discover_documentation_files()

        summary = {
            'files_processed': 0,
            'files_updated': 0,
            'references_updated': 0,
            'errors': []
        }

        for file_path in files:
            try:
                if self._update_file_references(file_path, dry_run):
                    summary['files_updated'] += 1
                    summary['references_updated'] += 1
                summary['files_processed'] += 1

            except Exception as e:
                summary['errors'].append({
                    'file': str(file_path),
                    'error': str(e)
                })

        return summary

    def _update_file_references(self, file_path: Path, dry_run: bool = False) -> bool:
        """Update references in a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            updated = False

            # Update path references
            for old_path, new_path in self.path_mappings.items():
                if old_path in content:
                    content = content.replace(old_path, new_path)
                    updated = True

            # Update file references
            for old_file, new_file in self.file_mappings.items():
                if old_file in content:
                    content = content.replace(old_file, new_file)
                    updated = True

            # Update import references in documentation
            content = self._update_import_references(content)
            if content != original_content:
                updated = True

            # Update cross-references
            content = self._update_cross_references(content, file_path)
            if content != original_content:
                updated = True

            # Update links
            content = self._update_links(content, file_path)
            if content != original_content:
                updated = True

            if updated and not dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

            return updated

        except Exception as e:
            print(f"Error updating {file_path}: {e}")
            return False

    def _update_import_references(self, content: str) -> str:
        """Update import references in documentation."""
        # Update Python import examples
        import_patterns = [
            (r'from nautilus_trader\.', 'from nautilus_trader_engine.'),
            (r'import nautilus_trader', 'import nautilus_trader_engine'),
            (r'nautilus_trader\.', 'nautilus_trader_engine.'),
        ]

        for pattern, replacement in import_patterns:
            content = re.sub(pattern, replacement, content)

        return content

    def _update_cross_references(self, content: str, file_path: Path) -> str:
        """Update cross-references between documentation files."""
        # Update relative references
        ref_patterns = [
            (r'\.\./([^)]+\.md)', r'../docs/\1'),  # Update relative doc links
            (r'\.\./([^)]+\.rst)', r'../docs/\1'),
        ]

        for pattern, replacement in ref_patterns:
            content = re.sub(pattern, replacement, content)

        return content

    def _update_links(self, content: str, file_path: Path) -> str:
        """Update and validate links in documentation."""
        # Find markdown links
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        links = re.findall(link_pattern, content)

        for link_text, link_url in links:
            # Check if link is a file reference
            if not link_url.startswith(('http', 'https', 'mailto', '#')):
                # Try to resolve relative path
                try:
                    resolved_path = (file_path.parent / link_url).resolve()
                    if not resolved_path.exists():
                        # Try alternative locations
                        alt_paths = [
                            self.docs_dir / link_url,
                            self.project_root / link_url,
                            self.nautilus_package / link_url
                        ]

                        for alt_path in alt_paths:
                            if alt_path.exists():
                                # Update link to correct relative path
                                try:
                                    new_url = os.path.relpath(alt_path, file_path.parent)
                                    content = content.replace(
                                        f'[{link_text}]({link_url})',
                                        f'[{link_text}]({new_url})'
                                    )
                                    break
                                except ValueError:
                                    continue
                except (OSError, ValueError):
                    continue

        return content

    def validate_references(self, files: Optional[List[Path]] = None) -> Dict[str, Any]:
        """
        Validate documentation references.

        Args:
            files: Specific files to validate (None for all)

        Returns:
            Validation summary
        """
        if files is None:
            files = self.discover_documentation_files()

        validation_results = {
            'files_checked': 0,
            'broken_links': [],
            'missing_files': [],
            'invalid_references': [],
            'warnings': []
        }

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Validate links
                link_issues = self._validate_links(content, file_path)
                validation_results['broken_links'].extend(link_issues)

                # Validate file references
                file_issues = self._validate_file_references(content, file_path)
                validation_results['missing_files'].extend(file_issues)

                # Validate code references
                code_issues = self._validate_code_references(content, file_path)
                validation_results['invalid_references'].extend(code_issues)

                validation_results['files_checked'] += 1

            except Exception as e:
                validation_results['warnings'].append({
                    'file': str(file_path),
                    'message': f'Could not validate file: {e}'
                })

        return validation_results

    def _validate_links(self, content: str, file_path: Path) -> List[Dict[str, Any]]:
        """Validate links in content."""
        issues = []

        # Find markdown links
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        links = re.findall(link_pattern, content)

        for link_text, link_url in links:
            if not link_url.startswith(('http', 'https', 'mailto', '#')):
                # Check if file exists
                try:
                    target_path = (file_path.parent / link_url).resolve()
                    if not target_path.exists():
                        issues.append({
                            'file': str(file_path),
                            'link_text': link_text,
                            'link_url': link_url,
                            'issue': 'File not found'
                        })
                except (OSError, ValueError) as e:
                    issues.append({
                        'file': str(file_path),
                        'link_text': link_text,
                        'link_url': link_url,
                        'issue': str(e)
                    })

        return issues

    def _validate_file_references(self, content: str, file_path: Path) -> List[Dict[str, Any]]:
        """Validate file references in content."""
        issues = []

        # Look for file path patterns
        file_patterns = [
            r'`([^`]+\.py)`',  # Inline code with .py files
            r'([^\s]+\.py)',  # Plain .py file references
            r'([^\s]+\.md)',  # Markdown file references
        ]

        for pattern in file_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                # Skip URLs and obvious non-file references
                if any(skip in match for skip in ['http', 'https', 'github.com', 'example']):
                    continue

                # Try to resolve the file path
                potential_paths = [
                    file_path.parent / match,
                    self.docs_dir / match,
                    self.project_root / match,
                    self.nautilus_package / match
                ]

                found = False
                for path in potential_paths:
                    if path.exists():
                        found = True
                        break

                if not found:
                    issues.append({
                        'file': str(file_path),
                        'reference': match,
                        'issue': 'Referenced file not found'
                    })

        return issues

    def _validate_code_references(self, content: str, file_path: Path) -> List[Dict[str, Any]]:
        """Validate code references in documentation."""
        issues = []

        # Look for import statements in documentation
        import_lines = []
        in_code_block = False

        for line_num, line in enumerate(content.split('\n'), 1):
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue

            if in_code_block and ('import ' in line or 'from ' in line):
                import_lines.append((line_num, line.strip()))

        # Validate import statements
        for line_num, import_line in import_lines:
            # Extract module name
            if import_line.startswith('import '):
                module = import_line.split('import ')[1].split()[0]
            elif import_line.startswith('from '):
                module = import_line.split('from ')[1].split(' import ')[0]
            else:
                continue

            # Check if module exists
            if not self._module_exists(module):
                issues.append({
                    'file': str(file_path),
                    'line': line_num,
                    'reference': import_line,
                    'issue': f'Module {module} not found'
                })

        return issues

    def _module_exists(self, module_name: str) -> bool:
        """Check if a Python module exists."""
        try:
            __import__(module_name)
            return True
        except ImportError:
            # Check if it's a local module
            module_path = module_name.replace('.', '/')
            potential_files = [
                self.project_root / f"{module_path}.py",
                self.project_root / module_path / "__init__.py"
            ]
            return any(f.exists() for f in potential_files)

    def generate_index(self, output_file: Optional[Path] = None) -> str:
        """Generate a documentation index."""
        if output_file is None:
            output_file = self.docs_dir / "INDEX.md"

        doc_files = self.discover_documentation_files()
        doc_files = [f for f in doc_files if f.suffix in ['.md', '.rst']]

        # Categorize documentation
        categories = defaultdict(list)

        for file_path in doc_files:
            relative_path = file_path.relative_to(self.project_root)

            # Determine category based on path
            if 'api' in str(relative_path):
                categories['API Documentation'].append(relative_path)
            elif 'architecture' in str(relative_path):
                categories['Architecture'].append(relative_path)
            elif 'guides' in str(relative_path):
                categories['Guides'].append(relative_path)
            elif 'examples' in str(relative_path):
                categories['Examples'].append(relative_path)
            else:
                categories['General'].append(relative_path)

        # Generate index content
        content = "# Documentation Index\n\n"
        content += "This index provides an overview of all documentation files in the Nautilus Trader Engine project.\n\n"

        for category, files in sorted(categories.items()):
            content += f"## {category}\n\n"

            for file_path in sorted(files):
                # Create relative link
                link_path = file_path
                title = file_path.stem.replace('_', ' ').title()

                # Try to read title from file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        first_line = f.readline().strip()
                        if first_line.startswith('# '):
                            title = first_line[2:]
                except:
                    pass

                content += f"- [{title}]({link_path})\n"

            content += "\n"

        # Write index file
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)

        return content

    def fix_broken_links(self, files: Optional[List[Path]] = None,
                        dry_run: bool = False) -> Dict[str, Any]:
        """
        Fix broken links in documentation.

        Args:
            files: Specific files to check (None for all)
            dry_run: Show fixes without applying them

        Returns:
            Fix summary
        """
        if files is None:
            files = self.discover_documentation_files()

        summary = {
            'files_checked': 0,
            'links_fixed': 0,
            'links_not_fixed': 0
        }

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                original_content = content

                # Find and fix broken links
                content = self._fix_broken_links(content, file_path)

                if content != original_content:
                    if not dry_run:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)

                    summary['links_fixed'] += 1
                else:
                    summary['links_not_fixed'] += 1

                summary['files_checked'] += 1

            except Exception as e:
                print(f"Error processing {file_path}: {e}")

        return summary

    def _fix_broken_links(self, content: str, file_path: Path) -> str:
        """Fix broken links in content."""
        # This is a simplified implementation
        # In practice, you'd have more sophisticated link fixing logic

        # Find markdown links
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        links = re.findall(link_pattern, content)

        for link_text, link_url in links:
            if not link_url.startswith(('http', 'https', 'mailto', '#')):
                # Try to find the file in common locations
                alt_urls = [
                    f"../docs/{link_url}",
                    f"../../docs/{link_url}",
                    f"../../../docs/{link_url}",
                    f"docs/{link_url}",
                ]

                for alt_url in alt_urls:
                    alt_path = (file_path.parent / alt_url).resolve()
                    if alt_path.exists():
                        content = content.replace(
                            f'[{link_text}]({link_url})',
                            f'[{link_text}]({alt_url})'
                        )
                        break

        return content


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Documentation Reference Updater for Nautilus Trader Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Update command
    update_parser = subparsers.add_parser('update', help='Update documentation references')
    update_parser.add_argument('--files', nargs='*', help='Specific files to update')
    update_parser.add_argument('--dry-run', action='store_true', help='Show changes without applying')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate documentation references')
    validate_parser.add_argument('--files', nargs='*', help='Specific files to validate')

    # Index command
    index_parser = subparsers.add_parser('index', help='Generate documentation index')
    index_parser.add_argument('--output', help='Output file for index')

    # Fix-links command
    fix_parser = subparsers.add_parser('fix-links', help='Fix broken links in documentation')
    fix_parser.add_argument('--files', nargs='*', help='Specific files to check')
    fix_parser.add_argument('--dry-run', action='store_true', help='Show fixes without applying')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    updater = DocumentationReferenceUpdater()

    try:
        if args.command == 'update':
            files = [Path(f) for f in getattr(args, 'files', [])] if getattr(args, 'files', None) else None
            summary = updater.update_references(files, getattr(args, 'dry_run', False))

            print("Documentation Update Summary:")
            print(f"  Files processed: {summary['files_processed']}")
            print(f"  Files updated: {summary['files_updated']}")
            print(f"  References updated: {summary['references_updated']}")

            if summary['errors']:
                print(f"  Errors: {len(summary['errors'])}")
                for error in summary['errors'][:5]:  # Show first 5 errors
                    print(f"    {error['file']}: {error['error']}")

        elif args.command == 'validate':
            files = [Path(f) for f in getattr(args, 'files', [])] if getattr(args, 'files', None) else None
            results = updater.validate_references(files)

            print("Documentation Validation Results:")
            print(f"  Files checked: {results['files_checked']}")
            print(f"  Broken links: {len(results['broken_links'])}")
            print(f"  Missing files: {len(results['missing_files'])}")
            print(f"  Invalid references: {len(results['invalid_references'])}")

            if results['broken_links']:
                print("\nBroken Links:")
                for link in results['broken_links'][:10]:  # Show first 10
                    print(f"  {link['file']}: [{link['link_text']}]({link['link_url']}) - {link['issue']}")

        elif args.command == 'index':
            output_file = Path(getattr(args, 'output', 'docs/INDEX.md')) if getattr(args, 'output', None) else None
            index_content = updater.generate_index(output_file)

            if output_file:
                print(f"Documentation index generated: {output_file}")
            else:
                print("Generated documentation index:")
                print(index_content[:500] + "..." if len(index_content) > 500 else index_content)

        elif args.command == 'fix-links':
            files = [Path(f) for f in getattr(args, 'files', [])] if getattr(args, 'files', None) else None
            summary = updater.fix_broken_links(files, getattr(args, 'dry_run', False))

            print("Link Fixing Summary:")
            print(f"  Files checked: {summary['files_checked']}")
            print(f"  Links fixed: {summary['links_fixed']}")
            print(f"  Links not fixed: {summary['links_not_fixed']}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == '__main__':
    main()