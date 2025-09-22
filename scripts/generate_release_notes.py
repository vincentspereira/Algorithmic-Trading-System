#!/usr/bin/env python3
"""
Release Notes Generator for Nautilus Trader Engine.

This script generates comprehensive release notes from Git history,
pull requests, and issue tracking for automated releases.

Features:
- Automated changelog generation
- PR and issue categorization
- Contributor recognition
- Breaking changes highlighting
- Version comparison and diff analysis

Usage:
    python scripts/generate_release_notes.py --tag v1.2.3 --output release_notes.md
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import re

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class ReleaseNotesGenerator:
    """
    Generate comprehensive release notes from Git history and GitHub data.

    Analyzes commits, pull requests, and issues to create detailed
    release documentation with proper categorization and formatting.
    """

    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path or Path(__file__).parent.parent
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.repo_name = os.getenv('GITHUB_REPOSITORY', 'unknown/repo')

    def generate_release_notes(self, tag: str, previous_tag: Optional[str] = None,
                             output_format: str = 'markdown') -> str:
        """
        Generate release notes for a specific tag.

        Args:
            tag: Current release tag
            previous_tag: Previous release tag for comparison
            output_format: Output format ('markdown', 'html', 'json')

        Returns:
            Formatted release notes
        """
        print(f"Generating release notes for {tag}...")

        # Get release information
        release_info = self._get_release_info(tag, previous_tag)

        # Categorize changes
        categorized_changes = self._categorize_changes(release_info['commits'])

        # Generate formatted output
        if output_format == 'markdown':
            return self._generate_markdown(release_info, categorized_changes)
        elif output_format == 'html':
            return self._generate_html(release_info, categorized_changes)
        elif output_format == 'json':
            return self._generate_json(release_info, categorized_changes)
        else:
            raise ValueError(f"Unsupported format: {output_format}")

    def _get_release_info(self, tag: str, previous_tag: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive release information."""
        # Get tag information
        tag_info = self._get_tag_info(tag)

        # Determine previous tag if not provided
        if not previous_tag:
            previous_tag = self._get_previous_tag(tag)

        # Get commits between tags
        commits = self._get_commits_between_tags(previous_tag, tag)

        # Get pull requests
        pull_requests = self._get_pull_requests(previous_tag, tag)

        # Get contributors
        contributors = self._get_contributors(commits)

        # Analyze breaking changes
        breaking_changes = self._analyze_breaking_changes(commits, pull_requests)

        return {
            'tag': tag,
            'previous_tag': previous_tag,
            'date': tag_info.get('date', datetime.now().isoformat()),
            'commits': commits,
            'pull_requests': pull_requests,
            'contributors': contributors,
            'breaking_changes': breaking_changes,
            'stats': {
                'total_commits': len(commits),
                'total_prs': len(pull_requests),
                'total_contributors': len(contributors),
                'breaking_changes_count': len(breaking_changes)
            }
        }

    def _get_tag_info(self, tag: str) -> Dict[str, Any]:
        """Get information about a Git tag."""
        try:
            # Get tag date
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%ai', tag],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            date = result.stdout.strip()

            # Get tag message
            result = subprocess.run(
                ['git', 'tag', '-l', '--format=%(contents)', tag],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            message = result.stdout.strip()

            return {
                'date': date,
                'message': message
            }

        except subprocess.CalledProcessError:
            return {'date': datetime.now().isoformat(), 'message': ''}

    def _get_previous_tag(self, current_tag: str) -> str:
        """Get the previous tag in chronological order."""
        try:
            result = subprocess.run(
                ['git', 'tag', '--sort=-version:refname'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )

            tags = result.stdout.strip().split('\n')
            tags = [tag for tag in tags if tag.strip()]

            # Find current tag and return previous one
            try:
                current_index = tags.index(current_tag)
                if current_index + 1 < len(tags):
                    return tags[current_index + 1]
            except ValueError:
                pass

            # Fallback: return the most recent tag
            return tags[0] if tags else 'HEAD~1'

        except subprocess.CalledProcessError:
            return 'HEAD~1'

    def _get_commits_between_tags(self, from_tag: str, to_tag: str) -> List[Dict[str, Any]]:
        """Get all commits between two tags."""
        try:
            # Get commit information
            result = subprocess.run(
                ['git', 'log', '--pretty=format:%H|%an|%ae|%s|%D', f'{from_tag}..{to_tag}'],
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
                            'refs': refs,
                            'type': self._classify_commit_type(subject)
                        })

            return commits

        except subprocess.CalledProcessError:
            return []

    def _classify_commit_type(self, subject: str) -> str:
        """Classify commit type based on conventional commit format."""
        subject_lower = subject.lower()

        if subject.startswith('feat:') or subject.startswith('feat('):
            return 'feature'
        elif subject.startswith('fix:') or subject.startswith('fix('):
            return 'bugfix'
        elif subject.startswith('docs:') or subject.startswith('docs('):
            return 'documentation'
        elif subject.startswith('style:') or subject.startswith('style('):
            return 'style'
        elif subject.startswith('refactor:') or subject.startswith('refactor('):
            return 'refactor'
        elif subject.startswith('test:') or subject.startswith('test('):
            return 'test'
        elif subject.startswith('chore:') or subject.startswith('chore('):
            return 'chore'
        elif subject.startswith('perf:') or subject.startswith('perf('):
            return 'performance'
        elif subject.startswith('ci:') or subject.startswith('ci('):
            return 'ci'
        elif subject.startswith('build:') or subject.startswith('build('):
            return 'build'
        elif 'break' in subject_lower or 'breaking' in subject_lower:
            return 'breaking'
        else:
            return 'other'

    def _get_pull_requests(self, from_tag: str, to_tag: str) -> List[Dict[str, Any]]:
        """Get pull requests merged between tags."""
        # This would integrate with GitHub API
        # For now, return empty list as placeholder
        return []

    def _get_contributors(self, commits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get list of contributors from commits."""
        contributors = {}

        for commit in commits:
            author = commit['author']
            email = commit['email']

            if author not in contributors:
                contributors[author] = {
                    'name': author,
                    'email': email,
                    'commits': 0,
                    'types': set()
                }

            contributors[author]['commits'] += 1
            contributors[author]['types'].add(commit['type'])

        # Convert to list and sort by commit count
        contributor_list = list(contributors.values())
        contributor_list.sort(key=lambda x: x['commits'], reverse=True)

        return contributor_list

    def _analyze_breaking_changes(self, commits: List[Dict[str, Any]],
                                pull_requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze commits and PRs for breaking changes."""
        breaking_changes = []

        # Check commits for breaking change indicators
        for commit in commits:
            if commit['type'] == 'breaking':
                breaking_changes.append({
                    'type': 'commit',
                    'title': commit['subject'],
                    'author': commit['author'],
                    'hash': commit['hash']
                })

        # Check PRs for breaking changes (would be enhanced with GitHub API)
        for pr in pull_requests:
            if pr.get('breaking', False):
                breaking_changes.append({
                    'type': 'pr',
                    'title': pr.get('title', ''),
                    'number': pr.get('number', 0),
                    'author': pr.get('author', '')
                })

        return breaking_changes

    def _categorize_changes(self, commits: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize commits by type."""
        categories = {
            'features': [],
            'bugfixes': [],
            'documentation': [],
            'performance': [],
            'refactoring': [],
            'testing': [],
            'ci': [],
            'other': []
        }

        for commit in commits:
            commit_type = commit['type']

            if commit_type == 'feature':
                categories['features'].append(commit)
            elif commit_type == 'bugfix':
                categories['bugfixes'].append(commit)
            elif commit_type == 'documentation':
                categories['documentation'].append(commit)
            elif commit_type == 'performance':
                categories['performance'].append(commit)
            elif commit_type == 'refactor':
                categories['refactoring'].append(commit)
            elif commit_type == 'test':
                categories['testing'].append(commit)
            elif commit_type == 'ci':
                categories['ci'].append(commit)
            else:
                categories['other'].append(commit)

        return categories

    def _generate_markdown(self, release_info: Dict[str, Any],
                          categorized_changes: Dict[str, List[Dict[str, Any]]]) -> str:
        """Generate markdown-formatted release notes."""
        lines = []

        # Header
        lines.append(f"# Release {release_info['tag']}")
        lines.append("")
        lines.append(f"**Released:** {release_info['date'][:10]}")
        lines.append(f"**Previous Release:** {release_info['previous_tag']}")
        lines.append("")

        # Statistics
        stats = release_info['stats']
        lines.append("## 📊 Statistics")
        lines.append("")
        lines.append(f"- **Commits:** {stats['total_commits']}")
        lines.append(f"- **Pull Requests:** {stats['total_prs']}")
        lines.append(f"- **Contributors:** {stats['total_contributors']}")
        lines.append(f"- **Breaking Changes:** {stats['breaking_changes_count']}")
        lines.append("")

        # Breaking Changes
        if release_info['breaking_changes']:
            lines.append("## ⚠️ Breaking Changes")
            lines.append("")
            for change in release_info['breaking_changes']:
                if change['type'] == 'commit':
                    lines.append(f"- {change['title']} (by {change['author']})")
                else:
                    lines.append(f"- {change['title']} (#{change['number']} by {change['author']})")
            lines.append("")

        # Changes by category
        lines.append("## 📝 Changes")
        lines.append("")

        category_emojis = {
            'features': '✨',
            'bugfixes': '🐛',
            'documentation': '📚',
            'performance': '⚡',
            'refactoring': '🔄',
            'testing': '🧪',
            'ci': '🤖',
            'other': '📝'
        }

        category_titles = {
            'features': 'New Features',
            'bugfixes': 'Bug Fixes',
            'documentation': 'Documentation',
            'performance': 'Performance Improvements',
            'refactoring': 'Code Refactoring',
            'testing': 'Testing',
            'ci': 'CI/CD',
            'other': 'Other Changes'
        }

        for category, commits in categorized_changes.items():
            if commits:
                emoji = category_emojis.get(category, '📝')
                title = category_titles.get(category, category.title())
                lines.append(f"### {emoji} {title}")
                lines.append("")

                for commit in commits:
                    # Clean up commit subject
                    subject = commit['subject']
                    if ':' in subject:
                        subject = subject.split(':', 1)[1].strip()

                    lines.append(f"- {subject} (by {commit['author']})")

                lines.append("")

        # Contributors
        if release_info['contributors']:
            lines.append("## 👥 Contributors")
            lines.append("")
            lines.append("Thank you to all contributors!")
            lines.append("")

            for contributor in release_info['contributors'][:10]:  # Top 10
                types = ', '.join(sorted(contributor['types']))
                lines.append(f"- **{contributor['name']}** ({contributor['commits']} commits) - {types}")

            if len(release_info['contributors']) > 10:
                lines.append(f"- ... and {len(release_info['contributors']) - 10} more contributors")

            lines.append("")

        # Footer
        lines.append("---")
        lines.append("")
        lines.append("*This release was generated automatically.*")
        lines.append("")
        lines.append(f"[View on GitHub](https://github.com/{self.repo_name}/releases/tag/{release_info['tag']})")

        return "\n".join(lines)

    def _generate_html(self, release_info: Dict[str, Any],
                      categorized_changes: Dict[str, List[Dict[str, Any]]]) -> str:
        """Generate HTML-formatted release notes."""
        # Basic HTML conversion of markdown (simplified)
        markdown = self._generate_markdown(release_info, categorized_changes)

        # Simple markdown to HTML conversion
        html = markdown.replace('# ', '<h1>').replace('## ', '<h2>').replace('### ', '<h3>')
        html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
        html = html.replace('\n- ', '\n<li>').replace('\n\n', '</li>\n\n')
        html = f"<html><body>{html}</body></html>"

        return html

    def _generate_json(self, release_info: Dict[str, Any],
                      categorized_changes: Dict[str, List[Dict[str, Any]]]) -> str:
        """Generate JSON-formatted release notes."""
        data = {
            'release': release_info,
            'changes': categorized_changes
        }

        return json.dumps(data, indent=2, default=str)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate release notes for Nautilus Trader Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--tag', required=True, help='Release tag')
    parser.add_argument('--previous-tag', help='Previous release tag')
    parser.add_argument('--output', '-o', help='Output file')
    parser.add_argument('--format', choices=['markdown', 'html', 'json'],
                       default='markdown', help='Output format')

    args = parser.parse_args()

    generator = ReleaseNotesGenerator()

    try:
        release_notes = generator.generate_release_notes(
            tag=args.tag,
            previous_tag=args.previous_tag,
            output_format=args.format
        )

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(release_notes)
            print(f"Release notes written to {args.output}")
        else:
            print(release_notes)

    except Exception as e:
        print(f"Error generating release notes: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()