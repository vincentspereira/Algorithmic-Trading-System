#!/usr/bin/env python3
"""
Import Manager for Nautilus Trader Engine.

This script analyzes, validates, and fixes import statements throughout
the codebase to ensure consistency and correctness.

Features:
- Import statement analysis and validation
- Circular import detection
- Missing import detection
- Unused import cleanup
- Import organization and sorting
- Relative vs absolute import conversion
- Automated import fixing

Usage:
    python scripts/import_manager.py [command] [options]

Commands:
    analyze     Analyze import statements in the codebase
    fix         Automatically fix import issues
    validate   Validate import correctness
    circular   Detect circular imports
    unused     Find unused imports
    organize   Organize and sort imports
"""

import os
import re
import ast
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple, Optional
from collections import defaultdict
import subprocess

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
NAUTILUS_PACKAGE = PROJECT_ROOT / "nautilus_trader_engine"


class ImportAnalyzer:
    """
    Analyzes Python import statements in the codebase.

    Provides comprehensive analysis of import patterns, dependencies,
    and potential issues.
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or PROJECT_ROOT
        self.nautilus_package = NAUTILUS_PACKAGE
        self.python_files: List[Path] = []
        self.import_data: Dict[Path, Dict[str, Any]] = {}

    def discover_python_files(self) -> List[Path]:
        """Discover all Python files in the project."""
        python_files = []

        # Skip common directories
        skip_dirs = {
            '__pycache__', '.git', '.pytest_cache', 'node_modules',
            'build', 'dist', '.tox', '.coverage', 'htmlcov'
        }

        for root, dirs, files in os.walk(self.project_root):
            # Remove skipped directories
            dirs[:] = [d for d in dirs if d not in skip_dirs]

            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)

        self.python_files = python_files
        return python_files

    def analyze_imports(self, files: Optional[List[Path]] = None) -> Dict[Path, Dict[str, Any]]:
        """Analyze import statements in Python files."""
        if files is None:
            files = self.python_files or self.discover_python_files()

        import_data = {}

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content, filename=str(file_path))
                imports = self._extract_imports(tree)

                import_data[file_path] = {
                    'imports': imports,
                    'relative_imports': [imp for imp in imports if imp['type'] == 'relative'],
                    'absolute_imports': [imp for imp in imports if imp['type'] == 'absolute'],
                    'from_imports': [imp for imp in imports if imp['type'] == 'from'],
                    'star_imports': [imp for imp in imports if imp.get('is_star', False)],
                    'issues': self._analyze_import_issues(imports, file_path)
                }

            except Exception as e:
                import_data[file_path] = {
                    'error': str(e),
                    'imports': [],
                    'issues': []
                }

        self.import_data = import_data
        return import_data

    def _extract_imports(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract import statements from AST."""
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        'type': 'absolute',
                        'module': alias.name,
                        'as_name': alias.asname,
                        'is_star': False,
                        'line': node.lineno
                    })
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.append({
                        'type': 'from' if node.level == 0 else 'relative',
                        'module': node.module or '',
                        'name': alias.name,
                        'as_name': alias.asname,
                        'level': node.level,
                        'is_star': alias.name == '*',
                        'line': node.lineno
                    })

        return imports

    def _analyze_import_issues(self, imports: List[Dict[str, Any]], file_path: Path) -> List[Dict[str, Any]]:
        """Analyze potential issues with imports."""
        issues = []

        # Check for relative imports that could be absolute
        for imp in imports:
            if imp['type'] == 'relative':
                # Check if relative import can be converted to absolute
                absolute_module = self._relative_to_absolute(imp, file_path)
                if absolute_module and self._module_exists(absolute_module):
                    issues.append({
                        'type': 'relative_to_absolute',
                        'message': f"Relative import '{imp['module']}' can be absolute: '{absolute_module}'",
                        'line': imp['line'],
                        'import': imp
                    })

        # Check for potentially missing modules
        for imp in imports:
            module_name = imp.get('module') or imp.get('name', '')
            if module_name and not self._module_exists(module_name):
                # Skip standard library and known external modules
                if not self._is_standard_or_external_module(module_name):
                    issues.append({
                        'type': 'missing_module',
                        'message': f"Module '{module_name}' may not exist",
                        'line': imp['line'],
                        'import': imp
                    })

        # Check for star imports
        star_imports = [imp for imp in imports if imp.get('is_star', False)]
        if star_imports:
            for imp in star_imports:
                issues.append({
                    'type': 'star_import',
                    'message': "Avoid using 'from module import *'",
                    'line': imp['line'],
                    'import': imp
                })

        return issues

    def _relative_to_absolute(self, imp: Dict[str, Any], file_path: Path) -> Optional[str]:
        """Convert relative import to absolute."""
        if imp['type'] != 'relative' or imp['level'] == 0:
            return None

        # Calculate the absolute path
        current_dir = file_path.parent
        for _ in range(imp['level']):
            current_dir = current_dir.parent

        # Build the module path
        module_parts = []
        remaining_path = file_path.parent

        while remaining_path != current_dir:
            if remaining_path.name:
                module_parts.insert(0, remaining_path.name)
            remaining_path = remaining_path.parent

        if imp['module']:
            module_parts.extend(imp['module'].split('.'))

        absolute_module = '.'.join(module_parts)
        return absolute_module

    def _module_exists(self, module_name: str) -> bool:
        """Check if a module exists."""
        try:
            __import__(module_name)
            return True
        except ImportError:
            # Check if it's a local module
            module_path = module_name.replace('.', '/')
            potential_paths = [
                self.project_root / f"{module_path}.py",
                self.project_root / module_path / "__init__.py"
            ]

            return any(path.exists() for path in potential_paths)

    def _is_standard_or_external_module(self, module_name: str) -> bool:
        """Check if module is standard library or known external."""
        # Common standard library modules
        stdlib_modules = {
            'os', 'sys', 're', 'json', 'datetime', 'pathlib', 'typing',
            'collections', 'itertools', 'functools', 'operator', 'math',
            'random', 'statistics', 'decimal', 'fractions', 'ast', 'inspect',
            'logging', 'threading', 'multiprocessing', 'asyncio', 'concurrent',
            'subprocess', 'shutil', 'tempfile', 'glob', 'fnmatch', 'linecache',
            'pickle', 'copyreg', 'copy', 'pprint', 'reprlib', 'enum', 'numbers',
            'unittest', 'doctest', 'argparse', 'optparse', 'getopt', 'readline',
            'rlcompleter', 'sqlite3', 'zlib', 'gzip', 'bz2', 'lzma', 'zipfile',
            'tarfile', 'csv', 'configparser', 'netrc', 'xdrlib', 'plistlib',
            'hashlib', 'hmac', 'secrets', 'ssl', 'socket', 'mmap', 'contextvars',
            'weakref', 'gc', 'inspect', 'site', 'warnings', 'contextlib',
            'abc', 'atexit', 'traceback', 'future', 'keyword', 'ast', 'symtable',
            'symbol', 'token', 'tokenize', 'tabnanny', 'pyclbr', 'py_compile',
            'compileall', 'dis', 'pickletools', 'platform', 'errno', 'ctypes',
            'msvcrt', 'winreg', 'winsound', 'posix', 'pwd', 'spwd', 'grp',
            'crypt', 'termios', 'tty', 'pty', 'fcntl', 'pipes', 'resource',
            'nis', 'syslog', 'optparse', 'nntplib', 'poplib', 'imaplib', 'smtplib',
            'smtpd', 'telnetlib', 'uuid', 'socketserver', 'http', 'ftplib',
            'poplib', 'imaplib', 'nntplib', 'smtplib', 'smtpd', 'telnetlib',
            'uuid', 'urllib', 'urllib2', 'urlparse', 'cookielib', 'Cookie',
            'BaseHTTPServer', 'SimpleHTTPServer', 'CGIHTTPServer', 'wsgiref',
            'webbrowser', 'cgi', 'cgitb', 'wsgiref', 'xdrlib', 'plistlib'
        }

        # Common external modules used in this project
        external_modules = {
            'fastapi', 'uvicorn', 'pydantic', 'sqlalchemy', 'alembic',
            'redis', 'celery', 'pytest', 'numpy', 'pandas', 'scipy',
            'scikit', 'matplotlib', 'seaborn', 'plotly', 'dash',
            'jupyter', 'ipykernel', 'ta', 'yfinance', 'backtrader',
            'vectorbt', 'optuna', 'trading', 'finrl', 'stable', 'gymnasium',
            'opentelemetry', 'prometheus', 'structlog', 'loguru',
            'psutil', 'pyportfolioopt', 'riskfolio', 'quantlib', 'arch',
            'statsmodels', 'graphene', 'flask', 'graphql', 'bandit',
            'pre', 'python', 'passlib', 'bcrypt', 'multipart', 'alpha',
            'finnhub', 'twelvedata', 'polygon', 'oandapy', 'grpc', 'protobuf',
            'clickhouse', 'duckdb', 'psycopg2', 'pymongo', 'cassandra',
            'influxdb', 'kafka', 'asyncio', 'aioredis', 'mqtt', 'websockets',
            'jinja2', 'aiofiles', 'python-multipart', 'uvloop', 'gunicorn',
            'hypercorn', 'daphne', 'pytest-asyncio', 'httpx', 'requests',
            'aiohttp', 'tqdm', 'rich', 'typer', 'click', 'questionary',
            'cookiecutter', 'pypa', 'setuptools', 'wheel', 'twine', 'build',
            'pip', 'virtualenv', 'pipenv', 'poetry', 'black', 'isort', 'flake8',
            'mypy', 'pylint', 'bandit', 'safety', 'coverage', 'pytest-cov',
            'pytest-xdist', 'pytest-benchmark', 'pytest-mock', 'freezegun',
            'faker', 'factory-boy', 'responses', 'vcrpy', 'betamax', 'time-machine',
            'pendulum', 'arrow', 'dateutil', 'pytz', 'tzlocal', 'babel',
            'humanize', 'tabulate', 'colorama', 'termcolor', 'crayons',
            'halo', 'yaspin', 'alive-progress', 'tqdm', 'rich', 'textual',
            'pyfiglet', 'art', 'colorful', 'ansicolors', 'coloredlogs',
            'structlog', 'loguru', 'picologging', 'logbook', 'eliot',
            'python-json-logger', 'logstash-formatter', 'graypy', 'sentry-sdk',
            'rollbar', 'bugsnag', 'airbrake', 'raygun4py', 'opbeat', 'newrelic',
            'datadog', 'statsd', 'prometheus_client', 'influxdb-client',
            'cassandra-driver', 'pymongo', 'redis-py', 'pymysql', 'psycopg2-binary',
            'sqlite3', 'sqlalchemy', 'alembic', 'sqlalchemy-utils', 'sqlalchemy-mixins',
            'sqlalchemy-continuum', 'sqlalchemy-easy-softdelete', 'sqlalchemy-filters',
            'sqlalchemy-fulltext-search', 'sqlalchemy-json', 'sqlalchemy-searchable',
            'sqlalchemy-utils', 'dataset', 'records', 'peewee', 'pony', 'tortoise-orm',
            'piccolo', 'edgy', 'ormar', 'beanie', 'motor', 'aiomysql', 'aiomongo',
            'aioinflux', 'aiocassandra', 'aiokafka', 'aioredis', 'aiofiles',
            'aiohttp', 'httpx', 'requests', 'urllib3', 'requests-toolbelt',
            'requests-html', 'grequests', 'httpx', 'aiohttp-client-cache',
            'fastapi', 'starlette', 'uvicorn', 'gunicorn', 'hypercorn', 'daphne',
            'sanic', 'quart', 'falcon', 'hug', 'eve', 'flask', 'django', 'tornado',
            'bottle', 'cherrypy', 'web2py', 'pyramid', 'turbogears', 'pylons',
            'zope', 'grokk', 'bluebottle', 'morepath', 'klein', 'cyclone',
            'pydantic', 'marshmallow', 'cerberus', 'voluptuous', 'schema',
            'colander', 'formencode', 'wtforms', 'django-forms', 'flask-wtf',
            'pydantic-forms', 'fastapi-forms', 'streamlit', 'gradio', 'panel',
            'voila', 'dash', 'bokeh', 'plotly', 'matplotlib', 'seaborn',
            'altair', 'vega', 'ggplot', 'plotnine', 'holoviews', 'hvplot',
            'pandas', 'polars', 'dask', 'vaex', 'modin', 'ray', 'pyspark',
            'numpy', 'scipy', 'scikit-learn', 'xgboost', 'lightgbm', 'catboost',
            'tensorflow', 'pytorch', 'keras', 'jax', 'flax', 'haiku', 'optuna',
            'hyperopt', 'ray-tune', 'wandb', 'mlflow', 'comet-ml', 'neptune',
            'clearml', 'weights-biases', 'sacred', 'guild-ai', 'dvc', 'cml',
            'kedro', 'prefect', 'airflow', 'dagster', 'luigi', 'bonobo',
            'petl', 'pandas-profiling', 'sweetviz', 'dataprep', 'lux',
            'dtale', 'pandasgui', 'tabula-py', 'camelot', 'pdfplumber',
            'tabulate', 'prettytable', 'rich', 'textual', 'pyfiglet',
            'colorama', 'termcolor', 'crayons', 'coloredlogs', 'tqdm',
            'halo', 'yaspin', 'alive-progress', 'questionary', 'inquirer',
            'whaaaaat', 'bullet', 'prompt-toolkit', 'click', 'typer',
            'fire', 'docopt', 'plac', 'cliff', 'cement', 'cookiecutter',
            'copier', 'jinja2', 'mako', 'chameleon', 'genshi', 'kid',
            'pypa', 'setuptools', 'wheel', 'twine', 'build', 'poetry',
            'pip', 'pipenv', 'virtualenv', 'conda', 'mamba', 'micromamba',
            'pyenv', 'pyenv-virtualenv', 'direnv', 'asdf', 'nvm', 'rbenv',
            'black', 'isort', 'autoflake', 'autopep8', 'yapf', 'docformatter',
            'add-trailing-comma', 'pyupgrade', 'flynt', 'flake8', 'pylint',
            'mypy', 'pyright', 'pyre', 'bandit', 'safety', 'darglint',
            'doc8', 'pydocstyle', 'radon', 'xenon', 'cohesion', 'wily',
            'coverage', 'pytest', 'pytest-cov', 'pytest-xdist', 'pytest-benchmark',
            'pytest-mock', 'pytest-asyncio', 'pytest-django', 'pytest-flask',
            'pytest-fastapi', 'pytest-tornasync', 'freezegun', 'faker',
            'factory-boy', 'responses', 'vcrpy', 'betamax', 'time-machine',
            'pendulum', 'arrow', 'dateutil', 'pytz', 'tzlocal', 'babel',
            'humanize', 'inflect', 'num2words', 'word2number', 'roman',
            'tabulate', 'prettytable', 'terminaltables', 'asciitable',
            'texttable', 'textwrap', 'textwrap3', 'pyyaml', 'toml', 'tomli',
            'tomllib', 'configobj', 'configparser', 'python-decouple',
            'dynaconf', 'python-dotenv', 'environs', 'parse', 'sh',
            'delegator', 'invoke', 'fabric', 'pexpect', 'paramiko',
            'scp', 'sftp', 'ftplib', 'pysftp', 'asyncssh', 'twisted',
            'trio', 'curio', 'asyncio', 'uvloop', 'gevent', 'eventlet',
            'greenlet', 'stackless', 'multiprocessing', 'threading',
            'concurrent', 'subprocess', 'shutil', 'tempfile', 'pathlib',
            'os', 'sys', 'platform', 'getpass', 'hashlib', 'hmac',
            'secrets', 'ssl', 'socket', 'mmap', 'contextvars', 'weakref',
            'gc', 'tracemalloc', 'sys', 'resource', 'psutil', 'guppy3',
            'memory-profiler', 'line-profiler', 'cProfile', 'profile',
            'pstats', 'timeit', 'time', 'datetime', 'calendar', 'sched',
            'queue', 'heapq', '_thread', 'dummy_thread', 'io', 'codecs',
            'unicodedata', 'stringprep', 're', 'difflib', 'textwrap',
            'string', 'binary', 'struct', 'weakref', 'enum', 'numbers',
            'math', 'cmath', 'decimal', 'fractions', 'random', 'statistics',
            'functools', 'itertools', 'operator', 'collections', 'deque',
            'namedtuple', 'OrderedDict', 'Counter', 'defaultdict',
            'UserDict', 'UserList', 'UserString', 'array', 'bisect',
            'heapq', 'blist', 'sortedcontainers', 'pyrsistent', 'immutables',
            'attrs', 'dataclasses', 'typing', 'mypy_extensions', 'typing_extensions',
            'protocol', 'runtime_checkable', 'cast', 'overload', 'final',
            'Literal', 'Union', 'Optional', 'Any', 'NoReturn', 'ClassVar',
            'Generic', 'TypeVar', 'NewType', 'Callable', 'Tuple', 'List',
            'Dict', 'Set', 'FrozenSet', 'Deque', 'DefaultDict', 'OrderedDict',
            'Counter', 'ChainMap', 'Awaitable', 'Coroutine', 'AsyncIterable',
            'AsyncIterator', 'Iterable', 'Iterator', 'Reversible', 'Sized',
            'Container', 'Collection', 'AbstractSet', 'MutableSet', 'Mapping',
            'MutableMapping', 'Sequence', 'MutableSequence', 'ByteString',
            'Hashable', 'SupportsInt', 'SupportsFloat', 'SupportsComplex',
            'SupportsBytes', 'SupportsAbs', 'SupportsRound', 'Reversible',
            'ContextManager', 'AsyncContextManager', 'ast', 'inspect',
            'dis', 'compile', 'eval', 'exec', 'token', 'tokenize',
            'keyword', 'astor', 'codegen', 'unparse', 'meta', 'astmonkey',
            'astroid', 'pylint', 'flake8', 'autopep8', 'black', 'isort',
            'importlib', 'importlib.resources', 'importlib.metadata',
            'pkgutil', 'pkg_resources', 'setuptools', 'distutils',
            'zipimport', 'zipfile', 'tarfile', 'gzip', 'bz2', 'lzma',
            'zlib', 'base64', 'binascii', 'uu', 'quopri', 'mailcap',
            'mailbox', 'mhlib', 'mimify', 'multifile', 'rfc822', 'formatter',
            'email', 'imaplib', 'nntplib', 'poplib', 'smtplib', 'smtpd',
            'telnetlib', 'uuid', 'urllib', 'urllib2', 'urlparse', 'cookielib',
            'Cookie', 'BaseHTTPServer', 'SimpleHTTPServer', 'CGIHTTPServer',
            'wsgiref', 'webbrowser', 'cgi', 'cgitb', 'xdrlib', 'plistlib',
            'hashlib', 'hmac', 'secrets', 'ssl', 'socket', 'mmap',
            'contextvars', 'weakref', 'gc', 'inspect', 'site', 'warnings',
            'contextlib', 'abc', 'atexit', 'traceback', 'future', 'keyword',
            'ast', 'symtable', 'symbol', 'token', 'tokenize', 'tabnanny',
            'pyclbr', 'py_compile', 'compileall', 'dis', 'pickletools',
            'platform', 'errno', 'ctypes', 'msvcrt', 'winreg', 'winsound',
            'posix', 'pwd', 'spwd', 'grp', 'crypt', 'termios', 'tty', 'pty',
            'fcntl', 'pipes', 'resource', 'nis', 'syslog', 'optparse',
            'nntplib', 'poplib', 'imaplib', 'smtplib', 'smtpd', 'telnetlib',
            'uuid', 'socketserver', 'http', 'ftplib', 'poplib', 'imaplib',
            'nntplib', 'smtplib', 'smtpd', 'telnetlib', 'uuid', 'urllib',
            'urllib2', 'urlparse', 'cookielib', 'Cookie', 'BaseHTTPServer',
            'SimpleHTTPServer', 'CGIHTTPServer', 'wsgiref', 'webbrowser',
            'cgi', 'cgitb', 'xdrlib', 'plistlib', 'unittest', 'doctest',
            'argparse', 'optparse', 'getopt', 'readline', 'rlcompleter',
            'sqlite3', 'zlib', 'gzip', 'bz2', 'lzma', 'zipfile', 'tarfile',
            'csv', 'configparser', 'netrc', 'xdrlib', 'plistlib', 'hashlib',
            'hmac', 'secrets', 'ssl', 'socket', 'mmap', 'contextvars',
            'weakref', 'gc', 'inspect', 'site', 'warnings', 'contextlib',
            'abc', 'atexit', 'traceback', 'future', 'keyword', 'ast',
            'symtable', 'symbol', 'token', 'tokenize', 'tabnanny', 'pyclbr',
            'py_compile', 'compileall', 'dis', 'pickletools', 'platform',
            'errno', 'ctypes', 'msvcrt', 'winreg', 'winsound', 'posix',
            'pwd', 'spwd', 'grp', 'crypt', 'termios', 'tty', 'pty', 'fcntl',
            'pipes', 'resource', 'nis', 'syslog', 'optparse', 'nntplib',
            'poplib', 'imaplib', 'smtplib', 'smtpd', 'telnetlib', 'uuid',
            'socketserver', 'http', 'ftplib', 'poplib', 'imaplib', 'nntplib',
            'smtplib', 'smtpd', 'telnetlib', 'uuid', 'urllib', 'urllib2',
            'urlparse', 'cookielib', 'Cookie', 'BaseHTTPServer', 'SimpleHTTPServer',
            'CGIHTTPServer', 'wsgiref', 'webbrowser', 'cgi', 'cgitb', 'xdrlib',
            'plistlib'
        }

        # Check if it's a standard library module
        if module_name in stdlib_modules:
            return True

        # Check if it's a known external module (check first part)
        first_part = module_name.split('.')[0]
        if first_part in external_modules:
            return True

        return False

    def detect_circular_imports(self) -> List[Dict[str, Any]]:
        """Detect circular import dependencies."""
        # This is a simplified circular import detection
        # A full implementation would build a dependency graph

        circular_imports = []

        for file_path, data in self.import_data.items():
            if 'error' in data:
                continue

            file_module = self._file_to_module(file_path)

            for imp in data['imports']:
                if imp['type'] in ['relative', 'from']:
                    imported_module = self._resolve_import_module(imp, file_path)

                    # Check if the imported module imports this file
                    if imported_module and imported_module in self.import_data:
                        imported_data = self.import_data[imported_module]

                        # Check if imported module imports current module
                        for imported_imp in imported_data.get('imports', []):
                            imported_imp_module = self._resolve_import_module(imported_imp, imported_module)
                            if imported_imp_module == file_module:
                                circular_imports.append({
                                    'file1': file_path,
                                    'file2': imported_module,
                                    'import1': imp,
                                    'import2': imported_imp
                                })

        return circular_imports

    def _file_to_module(self, file_path: Path) -> str:
        """Convert file path to module name."""
        try:
            relative_path = file_path.relative_to(self.project_root)
            module_parts = []

            for part in relative_path.parts:
                if part.endswith('.py'):
                    part = part[:-3]
                module_parts.append(part)

            return '.'.join(module_parts)
        except ValueError:
            return str(file_path)

    def _resolve_import_module(self, imp: Dict[str, Any], file_path: Path) -> Optional[Path]:
        """Resolve import to actual file path."""
        if imp['type'] == 'absolute':
            module_name = imp['module']
        elif imp['type'] == 'from':
            module_name = imp['module']
        elif imp['type'] == 'relative':
            # Convert relative to absolute
            module_name = self._relative_to_absolute(imp, file_path)
        else:
            return None

        if not module_name:
            return None

        # Convert module name to file path
        module_path = module_name.replace('.', '/')

        # Try different extensions
        potential_files = [
            self.project_root / f"{module_path}.py",
            self.project_root / module_path / "__init__.py"
        ]

        for potential_file in potential_files:
            if potential_file.exists():
                return potential_file

        return None

    def find_unused_imports(self) -> Dict[Path, List[Dict[str, Any]]]:
        """Find potentially unused imports."""
        # This is a simplified unused import detection
        # A full implementation would use AST analysis to track usage

        unused_imports = {}

        for file_path, data in self.import_data.items():
            if 'error' in data:
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Simple heuristic: check if imported names appear in the file
                unused = []
                for imp in data['imports']:
                    if imp['type'] == 'from':
                        imported_name = imp.get('as_name') or imp['name']
                        # Skip if it's a star import or standard pattern
                        if imp.get('is_star') or imported_name in ['*']:
                            continue

                        # Check if the name is used in the file (simple regex)
                        if not re.search(r'\b' + re.escape(imported_name) + r'\b', content):
                            unused.append(imp)

                if unused:
                    unused_imports[file_path] = unused

            except Exception as e:
                unused_imports[file_path] = [{'error': str(e)}]

        return unused_imports

    def organize_imports(self, file_path: Path) -> str:
        """Organize and sort imports in a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)
            imports = self._extract_imports(tree)

            # Separate different types of imports
            standard_imports = []
            third_party_imports = []
            local_imports = []

            for imp in imports:
                if imp['type'] == 'absolute':
                    module = imp['module']
                    if self._is_standard_library_module(module):
                        standard_imports.append(imp)
                    elif self._is_local_module(module, file_path):
                        local_imports.append(imp)
                    else:
                        third_party_imports.append(imp)
                else:
                    # Keep relative and from imports as-is for now
                    local_imports.append(imp)

            # Sort each group
            standard_imports.sort(key=lambda x: x['module'])
            third_party_imports.sort(key=lambda x: x['module'])
            local_imports.sort(key=lambda x: (x.get('module', ''), x.get('name', '')))

            # Reconstruct import statements
            organized_imports = []

            # Add standard library imports
            for imp in standard_imports:
                if imp.get('as_name'):
                    organized_imports.append(f"import {imp['module']} as {imp['as_name']}")
                else:
                    organized_imports.append(f"import {imp['module']}")

            if standard_imports:
                organized_imports.append("")

            # Add third-party imports
            for imp in third_party_imports:
                if imp.get('as_name'):
                    organized_imports.append(f"import {imp['module']} as {imp['as_name']}")
                else:
                    organized_imports.append(f"import {imp['module']}")

            if third_party_imports:
                organized_imports.append("")

            # Add local imports
            for imp in local_imports:
                if imp['type'] == 'from':
                    from_part = imp['module']
                    import_part = imp['name']
                    as_part = f" as {imp['as_name']}" if imp.get('as_name') else ""
                    organized_imports.append(f"from {from_part} import {import_part}{as_part}")
                elif imp['type'] == 'relative':
                    dots = '.' * imp['level']
                    from_part = f"{dots}{imp['module']}" if imp['module'] else dots
                    import_part = imp['name']
                    as_part = f" as {imp['as_name']}" if imp.get('as_name') else ""
                    organized_imports.append(f"from {from_part} import {import_part}{as_part}")
                else:
                    # Absolute import
                    as_part = f" as {imp['as_name']}" if imp.get('as_name') else ""
                    organized_imports.append(f"import {imp['module']}{as_part}")

            return '\n'.join(organized_imports)

        except Exception as e:
            return f"# Error organizing imports: {e}"

    def _is_standard_library_module(self, module: str) -> bool:
        """Check if module is from standard library."""
        # Simplified check - in practice, you'd use sys.stdlib_module_names
        stdlib_modules = {
            'os', 'sys', 're', 'json', 'datetime', 'pathlib', 'typing',
            'collections', 'itertools', 'functools', 'operator', 'math',
            'random', 'statistics', 'ast', 'inspect', 'logging'
        }
        return module.split('.')[0] in stdlib_modules

    def _is_local_module(self, module: str, file_path: Path) -> bool:
        """Check if module is local to the project."""
        module_parts = module.split('.')
        potential_path = self.project_root

        for part in module_parts:
            potential_path = potential_path / part

        return (potential_path.with_suffix('.py').exists() or
                (potential_path / '__init__.py').exists())

    def generate_report(self, output_format: str = 'text') -> str:
        """Generate a comprehensive import analysis report."""
        if output_format == 'text':
            return self._generate_text_report()
        elif output_format == 'json':
            return self._generate_json_report()
        else:
            raise ValueError(f"Unsupported format: {output_format}")

    def _generate_text_report(self) -> str:
        """Generate text-based analysis report."""
        lines = []
        lines.append("=" * 80)
        lines.append("NAUTILUS TRADER ENGINE - IMPORT ANALYSIS REPORT")
        lines.append("=" * 80)
        lines.append("")

        total_files = len(self.import_data)
        total_imports = sum(len(data.get('imports', [])) for data in self.import_data.values())
        files_with_issues = sum(1 for data in self.import_data.values() if data.get('issues'))

        lines.append("SUMMARY:")
        lines.append(f"  Total Python files analyzed: {total_files}")
        lines.append(f"  Total import statements: {total_imports}")
        lines.append(f"  Files with import issues: {files_with_issues}")
        lines.append("")

        # Files with issues
        if files_with_issues > 0:
            lines.append("FILES WITH IMPORT ISSUES:")
            lines.append("-" * 50)

            for file_path, data in self.import_data.items():
                issues = data.get('issues', [])
                if issues:
                    lines.append(f"📁 {file_path.relative_to(self.project_root)}")
                    for issue in issues:
                        lines.append(f"  ⚠️  {issue['message']}")
                    lines.append("")

        # Import statistics
        lines.append("IMPORT STATISTICS:")
        lines.append("-" * 50)

        absolute_count = sum(len(data.get('absolute_imports', [])) for data in self.import_data.values())
        relative_count = sum(len(data.get('relative_imports', [])) for data in self.import_data.values())
        from_count = sum(len(data.get('from_imports', [])) for data in self.import_data.values())
        star_count = sum(len(data.get('star_imports', [])) for data in self.import_data.values())

        lines.append(f"  Absolute imports: {absolute_count}")
        lines.append(f"  Relative imports: {relative_count}")
        lines.append(f"  From imports: {from_count}")
        lines.append(f"  Star imports: {star_count}")
        lines.append("")

        return "\n".join(lines)

    def _generate_json_report(self) -> str:
        """Generate JSON-based analysis report."""
        return json.dumps({
            'summary': {
                'total_files': len(self.import_data),
                'total_imports': sum(len(data.get('imports', [])) for data in self.import_data.values()),
                'files_with_issues': sum(1 for data in self.import_data.values() if data.get('issues'))
            },
            'files': {
                str(file_path.relative_to(self.project_root)): data
                for file_path, data in self.import_data.items()
            }
        }, indent=2, default=str)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Import Manager for Nautilus Trader Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze import statements')
    analyze_parser.add_argument('--files', nargs='*', help='Specific files to analyze')
    analyze_parser.add_argument('--format', choices=['text', 'json'], default='text',
                               help='Output format')

    # Fix command
    fix_parser = subparsers.add_parser('fix', help='Automatically fix import issues')
    fix_parser.add_argument('--files', nargs='*', help='Specific files to fix')
    fix_parser.add_argument('--dry-run', action='store_true', help='Show what would be fixed')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate import correctness')
    validate_parser.add_argument('--files', nargs='*', help='Specific files to validate')

    # Circular command
    circular_parser = subparsers.add_parser('circular', help='Detect circular imports')

    # Unused command
    unused_parser = subparsers.add_parser('unused', help='Find unused imports')
    unused_parser.add_argument('--files', nargs='*', help='Specific files to check')

    # Organize command
    organize_parser = subparsers.add_parser('organize', help='Organize and sort imports')
    organize_parser.add_argument('--files', nargs='*', help='Specific files to organize')
    organize_parser.add_argument('--dry-run', action='store_true', help='Show what would be organized')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    analyzer = ImportAnalyzer()

    try:
        if args.command == 'analyze':
            files = [Path(f) for f in getattr(args, 'files', [])] if getattr(args, 'files', None) else None
            import_data = analyzer.analyze_imports(files)
            report = analyzer.generate_report(args.format)
            print(report)

        elif args.command == 'fix':
            # Placeholder for fix functionality
            print("Import fixing not yet implemented")
            print("Use 'organize' command to organize imports")

        elif args.command == 'validate':
            files = [Path(f) for f in getattr(args, 'files', [])] if getattr(args, 'files', None) else None
            import_data = analyzer.analyze_imports(files)

            issues_found = False
            for file_path, data in import_data.items():
                issues = data.get('issues', [])
                if issues:
                    issues_found = True
                    print(f"❌ {file_path.relative_to(analyzer.project_root)}")
                    for issue in issues:
                        print(f"  {issue['message']}")

            if not issues_found:
                print("✅ All imports are valid")

        elif args.command == 'circular':
            import_data = analyzer.analyze_imports()
            circular_imports = analyzer.detect_circular_imports()

            if circular_imports:
                print("🔄 CIRCULAR IMPORTS DETECTED:")
                print("-" * 50)
                for circular in circular_imports:
                    print(f"  {circular['file1'].relative_to(analyzer.project_root)}")
                    print(f"  ↔ {circular['file2'].relative_to(analyzer.project_root)}")
                    print()
            else:
                print("✅ No circular imports detected")

        elif args.command == 'unused':
            import_data = analyzer.analyze_imports()
            unused_imports = analyzer.find_unused_imports()

            if unused_imports:
                print("🗑️  POTENTIALLY UNUSED IMPORTS:")
                print("-" * 50)
                for file_path, imports in unused_imports.items():
                    print(f"📁 {file_path.relative_to(analyzer.project_root)}")
                    for imp in imports:
                        if 'error' in imp:
                            print(f"  ❌ Error: {imp['error']}")
                        else:
                            print(f"  ⚠️  Line {imp['line']}: {imp}")
                    print()
            else:
                print("✅ No unused imports detected")

        elif args.command == 'organize':
            files = getattr(args, 'files', None)
            if not files:
                # Discover all Python files
                analyzer.discover_python_files()
                files = [str(f.relative_to(analyzer.project_root)) for f in analyzer.python_files]

            dry_run = getattr(args, 'dry_run', False)

            for file_path_str in files:
                file_path = analyzer.project_root / file_path_str

                if not file_path.exists():
                    print(f"⚠️  File not found: {file_path_str}")
                    continue

                organized = analyzer.organize_imports(file_path)

                if dry_run:
                    print(f"📁 {file_path_str}")
                    print("Organized imports:")
                    print(organized)
                    print("-" * 50)
                else:
                    # Read original content
                    with open(file_path, 'r', encoding='utf-8') as f:
                        original_content = f.read()

                    # Find import section and replace
                    lines = original_content.split('\n')
                    import_lines = []
                    code_start = 0

                    # Find import statements at the beginning
                    for i, line in enumerate(lines):
                        stripped = line.strip()
                        if (stripped.startswith('import ') or
                            stripped.startswith('from ') or
                            stripped == '' and import_lines):
                            import_lines.append(line)
                        elif stripped and not stripped.startswith('#'):
                            code_start = i
                            break

                    if import_lines:
                        # Replace import section
                        new_content = '\n'.join(lines[:code_start])
                        new_content = new_content.replace('\n'.join(import_lines), organized)
                        new_content += '\n' + '\n'.join(lines[code_start:])

                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)

                        print(f"✅ Organized imports in {file_path_str}")
                    else:
                        print(f"⚠️  No imports found in {file_path_str}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()