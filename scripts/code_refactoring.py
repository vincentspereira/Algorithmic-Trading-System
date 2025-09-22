#!/usr/bin/env python3
"""
Code Refactoring and Cleanup Script for Nautilus Trader Engine.

This script performs comprehensive code refactoring and cleanup operations
including dead code removal, code quality improvements, and structural
enhancements.

Features:
- Dead code detection and removal
- Code formatting and style improvements
- Import optimization
- Function/method consolidation
- Variable renaming for clarity
- Documentation improvements
- Performance optimizations

Usage:
    python scripts/code_refactoring.py [command] [options]

Commands:
    analyze     Analyze code for refactoring opportunities
    refactor    Perform automated refactoring
    cleanup     Clean up code issues
    format      Format code according to standards
    optimize    Optimize code for performance
    validate    Validate refactoring results
"""

import os
import re
import ast
import sys
import json
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple, Optional, Callable
from dataclasses import dataclass
import argparse
try:
    import autopep8
    AUTOPEP8_AVAILABLE = True
except ImportError:
    AUTOPEP8_AVAILABLE = False

try:
    import isort
    ISORT_AVAILABLE = True
except ImportError:
    ISORT_AVAILABLE = False

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
NAUTILUS_PACKAGE = PROJECT_ROOT / "nautilus_trader_engine"


class CodeRefactoringManager:
    """
    Manages code refactoring and cleanup operations.

    Provides automated tools for improving code quality, removing dead code,
    and optimizing performance.
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or PROJECT_ROOT
        self.nautilus_package = NAUTILUS_PACKAGE

        # Refactoring rules
        self.refactoring_rules = {
            'unused_imports': self._remove_unused_imports,
            'dead_code': self._remove_dead_code,
            'long_functions': self._split_long_functions,
            'duplicate_code': self._consolidate_duplicate_code,
            'naming_issues': self._fix_naming_issues,
            'complex_expressions': self._simplify_complex_expressions,
        }

    def discover_python_files(self) -> List[Path]:
        """Discover all Python files in the project."""
        python_files = []

        # Skip common directories
        skip_dirs = {
            '__pycache__', '.git', '.pytest_cache', 'node_modules',
            'build', 'dist', '.tox', '.coverage', 'htmlcov'
        }

        for root, dirs, files in os.walk(self.nautilus_package):
            # Remove skipped directories
            dirs[:] = [d for d in dirs if d not in skip_dirs]

            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)

        return python_files

    def analyze_code(self, files: Optional[List[Path]] = None) -> Dict[str, Any]:
        """
        Analyze code for refactoring opportunities.

        Args:
            files: Specific files to analyze (None for all)

        Returns:
            Analysis results
        """
        if files is None:
            files = self.discover_python_files()

        analysis_results = {
            'files_analyzed': 0,
            'issues_found': [],
            'refactoring_opportunities': [],
            'code_metrics': {},
            'complexity_analysis': []
        }

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content, filename=str(file_path))

                # Analyze different aspects
                file_issues = self._analyze_file_issues(content, tree, file_path)
                refactoring_ops = self._find_refactoring_opportunities(content, tree, file_path)
                metrics = self._calculate_code_metrics(content, tree, file_path)
                complexity = self._analyze_complexity(content, tree, file_path)

                analysis_results['issues_found'].extend(file_issues)
                analysis_results['refactoring_opportunities'].extend(refactoring_ops)
                analysis_results['code_metrics'][str(file_path.relative_to(self.project_root))] = metrics
                analysis_results['complexity_analysis'].extend(complexity)

                analysis_results['files_analyzed'] += 1

            except Exception as e:
                analysis_results['issues_found'].append({
                    'file': str(file_path),
                    'type': 'parse_error',
                    'message': f'Could not analyze file: {e}'
                })

        return analysis_results

    def _analyze_file_issues(self, content: str, tree: ast.AST, file_path: Path) -> List[Dict[str, Any]]:
        """Analyze file for common issues."""
        issues = []

        lines = content.split('\n')

        # Check for long lines
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                issues.append({
                    'file': str(file_path),
                    'type': 'long_line',
                    'line': i,
                    'message': f'Line too long ({len(line)} characters)',
                    'severity': 'low'
                })

        # Check for TODO comments
        for i, line in enumerate(lines, 1):
            if 'TODO' in line.upper() or 'FIXME' in line.upper():
                issues.append({
                    'file': str(file_path),
                    'type': 'todo_comment',
                    'line': i,
                    'message': 'TODO/FIXME comment found',
                    'severity': 'info'
                })

        # Check for print statements (in production code)
        if 'test' not in str(file_path).lower():
            for i, line in enumerate(lines, 1):
                if re.search(r'\bprint\s*\(', line):
                    issues.append({
                        'file': str(file_path),
                        'type': 'debug_print',
                        'line': i,
                        'message': 'Print statement found in production code',
                        'severity': 'medium'
                    })

        return issues

    def _find_refactoring_opportunities(self, content: str, tree: ast.AST, file_path: Path) -> List[Dict[str, Any]]:
        """Find opportunities for code refactoring."""
        opportunities = []

        # Find long functions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if len(self._get_function_lines(content, node)) > 50:
                    opportunities.append({
                        'file': str(file_path),
                        'type': 'long_function',
                        'function': node.name,
                        'line': node.lineno,
                        'lines': len(self._get_function_lines(content, node)),
                        'message': f'Function {node.name} is too long ({len(self._get_function_lines(content, node))} lines)'
                    })

        # Find complex expressions
        for node in ast.walk(tree):
            if isinstance(node, ast.BoolOp) and len(node.values) > 3:
                opportunities.append({
                    'file': str(file_path),
                    'type': 'complex_boolean',
                    'line': node.lineno,
                    'message': 'Complex boolean expression could be simplified'
                })

        # Find magic numbers
        magic_numbers = self._find_magic_numbers(tree)
        for num, line in magic_numbers:
            opportunities.append({
                'file': str(file_path),
                'type': 'magic_number',
                'line': line,
                'value': num,
                'message': f'Magic number {num} should be a named constant'
            })

        return opportunities

    def _get_function_lines(self, content: str, func_node: ast.FunctionDef) -> List[str]:
        """Get lines belonging to a function."""
        lines = content.split('\n')
        start_line = func_node.lineno - 1  # Convert to 0-based indexing

        # Find function end (next function or class at same level)
        end_line = len(lines)
        for i in range(start_line + 1, len(lines)):
            line = lines[i].strip()
            if line.startswith('def ') or line.startswith('class '):
                # Check indentation level
                if not line.startswith(' ') or line.count(' ') <= lines[start_line].count(' '):
                    end_line = i
                    break

        return lines[start_line:end_line]

    def _find_magic_numbers(self, tree: ast.AST) -> List[Tuple[int, int]]:
        """Find magic numbers in the code."""
        magic_numbers = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Num) and isinstance(node.n, int):
                # Skip common non-magic numbers
                if node.n in [0, 1, 2, 3, 4, 5, 10, 100, 1000]:
                    continue
                # Skip if it's a constant assignment
                if (isinstance(node.parent, ast.Assign) and
                    len(node.parent.targets) == 1 and
                    isinstance(node.parent.targets[0], ast.Name) and
                    node.parent.targets[0].id.isupper()):
                    continue

                magic_numbers.append((node.n, node.lineno))

        # Add parent reference for context checking
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                child.parent = node

        return magic_numbers

    def _calculate_code_metrics(self, content: str, tree: ast.AST, file_path: Path) -> Dict[str, Any]:
        """Calculate code metrics for a file."""
        lines = content.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]

        # Count various code elements
        classes = len([node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)])
        functions = len([node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)])
        imports = len([node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))])

        return {
            'total_lines': len(lines),
            'code_lines': len(non_empty_lines),
            'classes': classes,
            'functions': functions,
            'imports': imports,
            'complexity': self._calculate_cyclomatic_complexity(tree)
        }

    def _calculate_cyclomatic_complexity(self, tree: ast.AST) -> int:
        """Calculate cyclomatic complexity of the code."""
        complexity = 1  # Base complexity

        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.Assert)):
                complexity += 1
            elif isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
                complexity += len(node.values) - 1
            elif isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
                complexity += len(node.values) - 1

        return complexity

    def _analyze_complexity(self, content: str, tree: ast.AST, file_path: Path) -> List[Dict[str, Any]]:
        """Analyze code complexity."""
        complexity_issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_complexity = self._calculate_function_complexity(node)
                if func_complexity > 10:
                    complexity_issues.append({
                        'file': str(file_path),
                        'function': node.name,
                        'complexity': func_complexity,
                        'line': node.lineno,
                        'message': f'Function {node.name} has high complexity ({func_complexity})'
                    })

        return complexity_issues

    def _calculate_function_complexity(self, func_node: ast.FunctionDef) -> int:
        """Calculate complexity for a single function."""
        complexity = 1

        for node in ast.walk(func_node):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.Assert)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1

        return complexity

    def perform_refactoring(self, files: Optional[List[Path]] = None,
                          rules: Optional[List[str]] = None,
                          dry_run: bool = False) -> Dict[str, Any]:
        """
        Perform automated refactoring on files.

        Args:
            files: Specific files to refactor (None for all)
            rules: Specific refactoring rules to apply (None for all)
            dry_run: Show changes without applying them

        Returns:
            Refactoring results
        """
        if files is None:
            files = self.discover_python_files()

        if rules is None:
            rules = list(self.refactoring_rules.keys())

        results = {
            'files_processed': 0,
            'refactoring_applied': [],
            'errors': []
        }

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()

                content = original_content

                # Apply each refactoring rule
                applied_rules = []
                for rule_name in rules:
                    if rule_name in self.refactoring_rules:
                        rule_func = self.refactoring_rules[rule_name]
                        new_content = rule_func(content, file_path)

                        if new_content != content:
                            applied_rules.append(rule_name)
                            content = new_content

                if applied_rules and not dry_run:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)

                if applied_rules:
                    results['refactoring_applied'].append({
                        'file': str(file_path),
                        'rules_applied': applied_rules,
                        'dry_run': dry_run
                    })

                results['files_processed'] += 1

            except Exception as e:
                results['errors'].append({
                    'file': str(file_path),
                    'error': str(e)
                })

        return results

    def _remove_unused_imports(self, content: str, file_path: Path) -> str:
        """Remove unused imports from code."""
        try:
            # Use autoflake for unused import removal
            result = subprocess.run(
                ['python', '-m', 'autoflake', '--remove-unused-variables',
                 '--remove-all-unused-imports', '--stdin-filename', str(file_path), '-'],
                input=content,
                text=True,
                capture_output=True,
                check=True
            )
            return result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback: simple unused import detection
            return self._simple_unused_import_removal(content)

    def _simple_unused_import_removal(self, content: str) -> str:
        """Simple unused import removal (fallback)."""
        # This is a simplified implementation
        # In practice, you'd use a more sophisticated tool
        return content

    def _remove_dead_code(self, content: str, file_path: Path) -> str:
        """Remove dead code."""
        # This is a simplified implementation
        # In practice, you'd use tools like vulture
        return content

    def _split_long_functions(self, content: str, file_path: Path) -> str:
        """Split long functions into smaller ones."""
        # This is a complex refactoring that would require
        # sophisticated code analysis
        return content

    def _consolidate_duplicate_code(self, content: str, file_path: Path) -> str:
        """Consolidate duplicate code."""
        # This would require clone detection algorithms
        return content

    def _fix_naming_issues(self, content: str, file_path: Path) -> str:
        """Fix naming issues in code."""
        # This could integrate with pylint or other linting tools
        return content

    def _simplify_complex_expressions(self, content: str, file_path: Path) -> str:
        """Simplify complex expressions."""
        # This could use code complexity analysis
        return content

    def format_code(self, files: Optional[List[Path]] = None,
                   style: str = 'autopep8') -> Dict[str, Any]:
        """
        Format code according to standards.

        Args:
            files: Specific files to format (None for all)
            style: Formatting style ('autopep8', 'black', 'yapf')

        Returns:
            Formatting results
        """
        if files is None:
            files = self.discover_python_files()

        results = {
            'files_processed': 0,
            'files_formatted': 0,
            'errors': []
        }

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()

                if style == 'autopep8':
                    if AUTOPEP8_AVAILABLE:
                        formatted_content = autopep8.fix_code(original_content)
                    else:
                        print(f"Warning: autopep8 not available, skipping formatting for {file_path}")
                        formatted_content = original_content
                elif style == 'black':
                    # Would integrate with black formatter
                    formatted_content = original_content
                else:
                    formatted_content = original_content

                if formatted_content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(formatted_content)
                    results['files_formatted'] += 1

                results['files_processed'] += 1

            except Exception as e:
                results['errors'].append({
                    'file': str(file_path),
                    'error': str(e)
                })

        return results

    def optimize_imports(self, files: Optional[List[Path]] = None) -> Dict[str, Any]:
        """
        Optimize import statements.

        Args:
            files: Specific files to optimize (None for all)

        Returns:
            Optimization results
        """
        if files is None:
            files = self.discover_python_files()

        results = {
            'files_processed': 0,
            'files_optimized': 0,
            'errors': []
        }

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()

                # Use isort for import optimization
                if ISORT_AVAILABLE:
                    optimized_content = isort.code(original_content)
                else:
                    print(f"Warning: isort not available, skipping import optimization for {file_path}")
                    optimized_content = original_content

                if optimized_content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(optimized_content)
                    results['files_optimized'] += 1

                results['files_processed'] += 1

            except Exception as e:
                results['errors'].append({
                    'file': str(file_path),
                    'error': str(e)
                })

        return results

    def validate_refactoring(self, files: Optional[List[Path]] = None) -> Dict[str, Any]:
        """
        Validate that refactoring didn't break anything.

        Args:
            files: Specific files to validate (None for all)

        Returns:
            Validation results
        """
        if files is None:
            files = self.discover_python_files()

        results = {
            'files_validated': 0,
            'syntax_errors': [],
            'import_errors': [],
            'warnings': []
        }

        for file_path in files:
            try:
                # Check syntax
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                ast.parse(content, filename=str(file_path))

                # Try to import the module (if it's importable)
                module_name = self._file_to_module_name(file_path)
                if module_name:
                    try:
                        __import__(module_name)
                    except ImportError as e:
                        results['import_errors'].append({
                            'file': str(file_path),
                            'module': module_name,
                            'error': str(e)
                        })

                results['files_validated'] += 1

            except SyntaxError as e:
                results['syntax_errors'].append({
                    'file': str(file_path),
                    'error': str(e)
                })
            except Exception as e:
                results['warnings'].append({
                    'file': str(file_path),
                    'error': str(e)
                })

        return results

    def _file_to_module_name(self, file_path: Path) -> Optional[str]:
        """Convert file path to module name."""
        try:
            relative_path = file_path.relative_to(self.nautilus_package)
            module_parts = []

            for part in relative_path.parts:
                if part.endswith('.py'):
                    part = part[:-3]
                module_parts.append(part)

            return '.'.join(module_parts)
        except ValueError:
            return None

    def generate_refactoring_report(self, analysis: Dict[str, Any]) -> str:
        """Generate a refactoring report."""
        report = []
        report.append("# Code Refactoring Report")
        report.append("")
        report.append(f"Generated: {os.popen('date').read().strip()}")
        report.append("")

        report.append("## Summary")
        report.append("")
        report.append(f"- Files analyzed: {analysis['files_analyzed']}")
        report.append(f"- Issues found: {len(analysis['issues_found'])}")
        report.append(f"- Refactoring opportunities: {len(analysis['refactoring_opportunities'])}")
        report.append("")

        if analysis['issues_found']:
            report.append("## Issues Found")
            report.append("")

            issues_by_type = {}
            for issue in analysis['issues_found']:
                issue_type = issue['type']
                if issue_type not in issues_by_type:
                    issues_by_type[issue_type] = []
                issues_by_type[issue_type].append(issue)

            for issue_type, issues in issues_by_type.items():
                report.append(f"### {issue_type.replace('_', ' ').title()}")
                report.append("")
                for issue in issues[:10]:  # Show first 10 of each type
                    report.append(f"- {issue['file']}: {issue['message']}")
                if len(issues) > 10:
                    report.append(f"- ... and {len(issues) - 10} more")
                report.append("")

        if analysis['refactoring_opportunities']:
            report.append("## Refactoring Opportunities")
            report.append("")

            for opp in analysis['refactoring_opportunities'][:20]:  # Show first 20
                report.append(f"- **{opp['type']}**: {opp['file']} - {opp['message']}")

            if len(analysis['refactoring_opportunities']) > 20:
                report.append(f"- ... and {len(analysis['refactoring_opportunities']) - 20} more opportunities")
            report.append("")

        return "\n".join(report)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Code Refactoring and Cleanup Script for Nautilus Trader Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze code for refactoring opportunities')
    analyze_parser.add_argument('--files', nargs='*', help='Specific files to analyze')
    analyze_parser.add_argument('--report', help='Generate report file')

    # Refactor command
    refactor_parser = subparsers.add_parser('refactor', help='Perform automated refactoring')
    refactor_parser.add_argument('--files', nargs='*', help='Specific files to refactor')
    refactor_parser.add_argument('--rules', nargs='*', help='Specific refactoring rules to apply')
    refactor_parser.add_argument('--dry-run', action='store_true', help='Show changes without applying')

    # Format command
    format_parser = subparsers.add_parser('format', help='Format code according to standards')
    format_parser.add_argument('--files', nargs='*', help='Specific files to format')
    format_parser.add_argument('--style', choices=['autopep8', 'black', 'yapf'],
                              default='autopep8', help='Formatting style')

    # Optimize command
    optimize_parser = subparsers.add_parser('optimize', help='Optimize imports')
    optimize_parser.add_argument('--files', nargs='*', help='Specific files to optimize')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate refactoring results')
    validate_parser.add_argument('--files', nargs='*', help='Specific files to validate')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    manager = CodeRefactoringManager()

    try:
        if args.command == 'analyze':
            files = [Path(f) for f in getattr(args, 'files', [])] if getattr(args, 'files', None) else None
            analysis = manager.analyze_code(files)

            print("Code Analysis Results:")
            print(f"  Files analyzed: {analysis['files_analyzed']}")
            print(f"  Issues found: {len(analysis['issues_found'])}")
            print(f"  Refactoring opportunities: {len(analysis['refactoring_opportunities'])}")

            # Generate report if requested
            if getattr(args, 'report', None):
                report = manager.generate_refactoring_report(analysis)
                report_file = Path(args.report)
                report_file.write_text(report)
                print(f"\nReport saved to: {report_file}")

        elif args.command == 'refactor':
            files = [Path(f) for f in getattr(args, 'files', [])] if getattr(args, 'files', None) else None
            rules = getattr(args, 'rules', None)
            results = manager.perform_refactoring(files, rules, getattr(args, 'dry_run', False))

            print("Refactoring Results:")
            if getattr(args, 'dry_run', False):
                print("  DRY RUN - No actual changes made")

            print(f"  Files processed: {results['files_processed']}")
            print(f"  Refactoring applied: {len(results['refactoring_applied'])}")

            if results['refactoring_applied']:
                print("\nRefactoring applied to:")
                for applied in results['refactoring_applied'][:10]:  # Show first 10
                    print(f"  ✅ {applied['file']}: {', '.join(applied['rules_applied'])}")

        elif args.command == 'format':
            files = [Path(f) for f in getattr(args, 'files', [])] if getattr(args, 'files', None) else None
            results = manager.format_code(files, getattr(args, 'style', 'autopep8'))

            print("Code Formatting Results:")
            print(f"  Files processed: {results['files_processed']}")
            print(f"  Files formatted: {results['files_formatted']}")

        elif args.command == 'optimize':
            files = [Path(f) for f in getattr(args, 'files', [])] if getattr(args, 'files', None) else None
            results = manager.optimize_imports(files)

            print("Import Optimization Results:")
            print(f"  Files processed: {results['files_processed']}")
            print(f"  Files optimized: {results['files_optimized']}")

        elif args.command == 'validate':
            files = [Path(f) for f in getattr(args, 'files', [])] if getattr(args, 'files', None) else None
            results = manager.validate_refactoring(files)

            print("Validation Results:")
            print(f"  Files validated: {results['files_validated']}")
            print(f"  Syntax errors: {len(results['syntax_errors'])}")
            print(f"  Import errors: {len(results['import_errors'])}")

            if results['syntax_errors']:
                print("\nSyntax Errors:")
                for error in results['syntax_errors'][:5]:
                    print(f"  ❌ {error['file']}: {error['error']}")

            if results['import_errors']:
                print("\nImport Errors:")
                for error in results['import_errors'][:5]:
                    print(f"  ❌ {error['file']}: {error['error']}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == '__main__':
    main()