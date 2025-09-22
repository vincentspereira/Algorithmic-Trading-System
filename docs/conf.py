"""
Sphinx configuration for Nautilus Trader Engine API documentation.

This configuration enables auto-generated API documentation from Python docstrings
using Sphinx with the autodoc extension.
"""

import os
import sys
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'nautilus_trader_engine'))

# Project information
project = 'Nautilus Trader Engine'
copyright = f'{datetime.now().year}, Trading System Team'
author = 'Trading System Team'
release = '1.0.0'
version = '1.0.0'

# General configuration
extensions = [
    'sphinx.ext.autodoc',      # Core autodoc functionality
    'sphinx.ext.autosummary',  # Generate autosummary tables
    'sphinx.ext.viewcode',     # Add source code links
    'sphinx.ext.napoleon',     # Support for NumPy/Google style docstrings
    'sphinx.ext.intersphinx',  # Link to external documentation
    'sphinx.ext.coverage',     # Check documentation coverage
    'sphinx.ext.doctest',      # Test code in docstrings
    'sphinx.ext.todo',         # Support for todo items
    'sphinx.ext.githubpages',  # GitHub Pages support
    'sphinx_rtd_theme',        # Read the Docs theme
]

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'exclude-members': '__weakref__'
}

# Autosummary settings
autosummary_generate = True
autosummary_imported_members = True

# Napoleon settings (Google/NumPy style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Intersphinx mapping
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'pandas': ('https://pandas.pydata.org/docs/', None),
    'scipy': ('https://docs.scipy.org/doc/scipy/', None),
    'matplotlib': ('https://matplotlib.org/stable/', None),
}

# HTML output configuration
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_css_files = [
    'css/custom.css',
]

# Theme options
html_theme_options = {
    'canonical_url': '',
    'analytics_id': '',
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'vcs_pageview_mode': '',
    'style_nav_header_background': '#2980B9',
    'collapse_navigation': True,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False
}

# HTML context
html_context = {
    'display_github': True,
    'github_user': 'your-username',
    'github_repo': 'nautilus-trader-engine',
    'github_version': 'main',
    'conf_py_path': '/docs/',
}

# Doctest configuration
doctest_global_setup = '''
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
'''

# Coverage configuration
coverage_modules = [
    'nautilus_trader_engine.core.*',
    'nautilus_trader_engine.analysis.*',
    'nautilus_trader_engine.strategies.*',
    'nautilus_trader_engine.engines.*',
]

# Todo configuration
todo_include_todos = True

# Source suffix
source_suffix = {
    '.rst': None,
    '.md': None,
}

# Master document
master_doc = 'index'

# Files to exclude
exclude_patterns = [
    '_build',
    'Thumbs.db',
    '.DS_Store',
    '**.ipynb_checkpoints',
]

# Pygments style
pygments_style = 'sphinx'

# Warning settings
nitpicky = True
nitpick_ignore = [
    ('py:class', 'type'),
    ('py:class', 'optional'),
    ('py:class', 'dict'),
    ('py:class', 'list'),
    ('py:class', 'tuple'),
    ('py:class', 'set'),
    ('py:class', 'frozenset'),
]