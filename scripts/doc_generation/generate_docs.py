"""
Script to generate API documentation and validate documentation quality.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List
from .doc_utils import (
    DocumentationIssue,
    validate_project_documentation,
    generate_project_documentation
)

def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Generate and validate API documentation"
    )
    
    parser.add_argument(
        "--project-path",
        type=str,
        required=True,
        help="Path to the project root"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="Directory for output files"
    )
    
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check documentation, don't generate"
    )
    
    parser.add_argument(
        "--fail-on",
        choices=['error', 'warning', 'info'],
        default='error',
        help="Minimum severity level to cause exit code 1"
    )
    
    return parser.parse_args()

def format_issues(issues: List[DocumentationIssue]) -> Dict:
    """Format documentation issues as JSON-compatible dict"""
    return {
        "total_issues": len(issues),
        "by_severity": {
            "error": len([i for i in issues if i.severity == 'error']),
            "warning": len([i for i in issues if i.severity == 'warning']),
            "info": len([i for i in issues if i.severity == 'info'])
        },
        "by_type": {},
        "issues": [
            {
                "file": issue.file_path,
                "line": issue.line_number,
                "type": issue.issue_type,
                "message": issue.message,
                "severity": issue.severity
            }
            for issue in issues
        ]
    }

def main() -> int:
    """Main entry point"""
    args = parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Validate documentation
    print("Validating documentation...")
    issues = validate_project_documentation(args.project_path)
    
    # Write validation report
    report_path = output_dir / "documentation_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(format_issues(issues), f, indent=2)
        
    print(f"Documentation validation report written to {report_path}")
    
    # Check if we should fail
    severity_levels = ['info', 'warning', 'error']
    fail_level = severity_levels.index(args.fail_on)
    
    has_failing_issues = any(
        severity_levels.index(i.severity) >= fail_level
        for i in issues
    )
    
    if has_failing_issues:
        print(
            f"Documentation validation failed: "
            f"found issues with severity >= {args.fail_on}"
        )
        if args.check_only:
            return 1
            
    if not args.check_only:
        # Generate documentation
        print("Generating API documentation...")
        docs_path = output_dir / "api_documentation.md"
        generate_project_documentation(args.project_path, str(docs_path))
        print(f"API documentation written to {docs_path}")
        
    return 1 if has_failing_issues else 0

if __name__ == '__main__':
    sys.exit(main())
