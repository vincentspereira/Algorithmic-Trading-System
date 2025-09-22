#!/usr/bin/env python3
"""
Documentation Generation Script for Nautilus Trader Engine.

This script automates the generation of comprehensive API documentation
using Sphinx with auto-generated content from Python docstrings.

Features:
- Auto-generates API documentation from code
- Creates HTML and PDF documentation
- Generates coverage reports for documentation
- Supports multiple output formats
- CI/CD integration ready

Usage:
    python scripts/generate_docs.py [options]

Options:
    --html          Generate HTML documentation (default)
    --pdf           Generate PDF documentation
    --coverage      Generate documentation coverage report
    --clean         Clean build directory before generation
    --serve         Start local documentation server
    --deploy        Deploy to GitHub Pages (CI/CD)
    --verbose       Verbose output
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path
from datetime import datetime


class DocumentationGenerator:
    """
    Automated documentation generator for the Nautilus Trader Engine.

    Handles the complete documentation generation pipeline including
    API docs, user guides, and deployment.
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.docs_dir = project_root / "docs"
        self.build_dir = self.docs_dir / "_build"
        self.source_dir = self.docs_dir
        self.api_dir = self.docs_dir / "api"

        # Ensure directories exist
        self.api_dir.mkdir(exist_ok=True)

    def clean_build_directory(self):
        """Clean the documentation build directory."""
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
            print("✓ Cleaned build directory")

    def check_dependencies(self):
        """Check if required documentation dependencies are installed."""
        required_packages = [
            'sphinx',
            'sphinx-rtd-theme',
            'sphinx-autodoc-typehints',
            'myst-parser'  # For Markdown support
        ]

        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                missing_packages.append(package)

        if missing_packages:
            print(f"⚠️  Missing documentation dependencies: {', '.join(missing_packages)}")
            print("Installing required packages...")
            try:
                subprocess.run([
                    sys.executable, '-m', 'pip', 'install',
                    '--quiet', *missing_packages
                ], check=True)
                print("✓ Dependencies installed")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install dependencies: {e}")
                return False

        return True

    def generate_api_docs(self):
        """Generate API documentation using sphinx-apidoc."""
        print("📚 Generating API documentation...")

        # Use sphinx-apidoc to auto-generate API docs
        cmd = [
            sys.executable, '-m', 'sphinx.ext.apidoc',
            '--force',  # Overwrite existing files
            '--module-first',  # Put module documentation before submodule docs
            '--separate',  # Put each module on separate page
            '--maxdepth', '4',  # Maximum depth for TOC
            '--output-dir', str(self.api_dir),
            '--doc-project', 'Nautilus Trader Engine API',
            str(self.project_root / 'nautilus_trader_engine')
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.docs_dir))

            if result.returncode == 0:
                print("✓ API documentation generated")
                if result.stdout:
                    print(result.stdout)
            else:
                print(f"⚠️  API generation warnings: {result.stderr}")
                return False

        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to generate API docs: {e}")
            return False

        return True

    def build_html_documentation(self):
        """Build HTML documentation using Sphinx."""
        print("🏗️  Building HTML documentation...")

        cmd = [
            sys.executable, '-m', 'sphinx',
            '-b', 'html',  # Builder
            '-E',  # Don't use cached environment
            '-v',  # Verbose
            str(self.source_dir),  # Source directory
            str(self.build_dir / 'html')  # Output directory
        ]

        try:
            result = subprocess.run(cmd, cwd=str(self.docs_dir))

            if result.returncode == 0:
                print("✓ HTML documentation built successfully")
                html_index = self.build_dir / 'html' / 'index.html'
                if html_index.exists():
                    print(f"📖 Documentation available at: file://{html_index}")
                return True
            else:
                print("❌ HTML build failed")
                return False

        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to build HTML docs: {e}")
            return False

    def build_pdf_documentation(self):
        """Build PDF documentation using Sphinx with LaTeX."""
        print("📄 Building PDF documentation...")

        # First build LaTeX
        latex_cmd = [
            sys.executable, '-m', 'sphinx',
            '-b', 'latex',
            str(self.source_dir),
            str(self.build_dir / 'latex')
        ]

        try:
            result = subprocess.run(latex_cmd, cwd=str(self.docs_dir))

            if result.returncode != 0:
                print("❌ LaTeX build failed")
                return False

            # Then build PDF from LaTeX (requires pdflatex)
            pdf_cmd = [
                'pdflatex',
                '-interaction=nonstopmode',
                'nautilustraderengine.tex'
            ]

            result = subprocess.run(pdf_cmd, cwd=str(self.build_dir / 'latex'))

            if result.returncode == 0:
                pdf_file = self.build_dir / 'latex' / 'nautilustraderengine.pdf'
                if pdf_file.exists():
                    print(f"✓ PDF documentation built: {pdf_file}")
                    return True

            print("❌ PDF build failed")
            return False

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"❌ PDF generation failed (pdflatex may not be installed): {e}")
            return False

    def generate_coverage_report(self):
        """Generate documentation coverage report."""
        print("📊 Generating documentation coverage report...")

        cmd = [
            sys.executable, '-m', 'sphinx.ext.coverage',
            str(self.source_dir),
            str(self.build_dir / 'coverage')
        ]

        try:
            result = subprocess.run(cmd, cwd=str(self.docs_dir))

            if result.returncode == 0:
                print("✓ Coverage report generated")
                return True
            else:
                print("❌ Coverage report generation failed")
                return False

        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to generate coverage report: {e}")
            return False

    def serve_documentation(self, port: int = 8000):
        """Start a local documentation server."""
        print(f"🚀 Starting documentation server on port {port}...")

        try:
            import http.server
            import socketserver
            import webbrowser

            # Change to HTML build directory
            html_dir = self.build_dir / 'html'
            if not html_dir.exists():
                print("❌ HTML documentation not found. Run --html first.")
                return False

            os.chdir(html_dir)

            # Start server
            with socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler) as httpd:
                print(f"✓ Server started at http://localhost:{port}")
                print("Press Ctrl+C to stop")

                # Open browser
                webbrowser.open(f"http://localhost:{port}")

                # Serve until interrupted
                httpd.serve_forever()

        except KeyboardInterrupt:
            print("\n✓ Server stopped")
            return True
        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            return False

    def deploy_to_github_pages(self):
        """Deploy documentation to GitHub Pages."""
        print("🚀 Deploying to GitHub Pages...")

        # This would typically be done in CI/CD
        # For now, just prepare the files
        html_dir = self.build_dir / 'html'

        if not html_dir.exists():
            print("❌ HTML documentation not found. Run --html first.")
            return False

        # Create .nojekyll file for GitHub Pages
        nojekyll_file = html_dir / '.nojekyll'
        nojekyll_file.touch()

        print("✓ Documentation prepared for GitHub Pages deployment")
        print(f"📁 HTML files ready in: {html_dir}")
        return True

    def run_complete_build(self, clean: bool = True, html: bool = True,
                          pdf: bool = False, coverage: bool = True):
        """Run complete documentation build pipeline."""
        print("🔄 Starting complete documentation build...")

        if clean:
            self.clean_build_directory()

        if not self.check_dependencies():
            return False

        if not self.generate_api_docs():
            return False

        if html and not self.build_html_documentation():
            return False

        if pdf and not self.build_pdf_documentation():
            return False

        if coverage and not self.generate_coverage_report():
            return False

        print("✅ Documentation build completed successfully!")
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Documentation Generator for Nautilus Trader Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--html', action='store_true', default=True,
                       help='Generate HTML documentation')
    parser.add_argument('--pdf', action='store_true',
                       help='Generate PDF documentation')
    parser.add_argument('--coverage', action='store_true', default=True,
                       help='Generate documentation coverage report')
    parser.add_argument('--clean', action='store_true',
                       help='Clean build directory before generation')
    parser.add_argument('--serve', action='store_true',
                       help='Start local documentation server')
    parser.add_argument('--deploy', action='store_true',
                       help='Deploy to GitHub Pages')
    parser.add_argument('--port', type=int, default=8000,
                       help='Port for local server (default: 8000)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')

    args = parser.parse_args()

    # Initialize generator
    project_root = Path(__file__).parent.parent
    generator = DocumentationGenerator(project_root)

    # Handle different modes
    if args.serve:
        success = generator.serve_documentation(args.port)
    elif args.deploy:
        success = generator.deploy_to_github_pages()
    else:
        # Complete build
        success = generator.run_complete_build(
            clean=args.clean,
            html=args.html,
            pdf=args.pdf,
            coverage=args.coverage
        )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()