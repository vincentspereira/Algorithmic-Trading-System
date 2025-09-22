# Nautilus Trader Engine Documentation

This directory contains the complete API documentation for the Nautilus Trader Engine, an institutional-grade algorithmic trading system.

## Overview

The documentation is auto-generated using Sphinx and provides comprehensive API reference, usage examples, and architectural documentation for all system components.

## Structure

```
docs/
├── conf.py                 # Sphinx configuration
├── index.rst              # Main documentation index
├── requirements.txt       # Documentation dependencies
├── README.md              # This file
├── api/                   # API documentation
│   ├── modules.rst        # Module overview
│   └── core.rst          # Core API reference
├── _static/               # Static assets (CSS, images, etc.)
└── _build/                # Generated documentation (auto-created)
```

## Building Documentation

### Prerequisites

Install documentation dependencies:

```bash
pip install -r docs/requirements.txt
```

### Quick Build

Use the automated documentation generator:

```bash
# Generate HTML documentation
python scripts/generate_docs.py --html

# Generate PDF documentation
python scripts/generate_docs.py --pdf

# Generate with coverage report
python scripts/generate_docs.py --coverage

# Clean and rebuild everything
python scripts/generate_docs.py --clean
```

### Manual Build

If you prefer manual control:

```bash
# Install dependencies
pip install sphinx sphinx-rtd-theme

# Generate API docs
sphinx-apidoc -f -o docs/api nautilus_trader_engine

# Build HTML
sphinx-build -b html docs docs/_build/html

# Build PDF (requires LaTeX)
sphinx-build -b latex docs docs/_build/latex
cd docs/_build/latex && pdflatex nautilustraderengine.tex
```

## Serving Documentation Locally

Start a local development server:

```bash
python scripts/generate_docs.py --serve
```

Or manually:

```bash
sphinx-build -b html docs docs/_build/html
cd docs/_build/html && python -m http.server 8000
```

Then visit `http://localhost:8000`

## Documentation Features

### Auto-generated API Docs

- **Complete API reference** for all modules
- **Inheritance diagrams** showing class hierarchies
- **Cross-references** between related components
- **Source code links** for detailed implementation

### Supported Formats

- **HTML**: Interactive web documentation
- **PDF**: Printable documentation
- **JSON**: Machine-readable API data
- **Coverage reports**: Documentation completeness metrics

### Content Types

- **Module documentation**: Overview of each system component
- **Class documentation**: Detailed class and method references
- **Function documentation**: Parameter and return value specifications
- **Example code**: Usage examples and code snippets
- **Architecture docs**: System design and component interactions

## CI/CD Integration

The documentation can be automatically built and deployed as part of your CI/CD pipeline:

```yaml
# GitHub Actions example
- name: Build Documentation
  run: python scripts/generate_docs.py --html --coverage

- name: Deploy to GitHub Pages
  run: python scripts/generate_docs.py --deploy
```

## Customization

### Adding New Modules

1. Add your module to `docs/api/modules.rst`
2. Create a corresponding `.rst` file in `docs/api/`
3. Add automodule directives for your classes/functions

### Styling

Custom CSS can be added to `docs/_static/css/custom.css`

### Configuration

Modify `docs/conf.py` to change:
- Project information
- Extensions and themes
- Build settings
- Cross-reference mappings

## Contributing

When adding new code:

1. **Write comprehensive docstrings** using Google/NumPy style
2. **Include type hints** for better API documentation
3. **Add examples** in docstrings where helpful
4. **Update module documentation** if adding new modules

### Docstring Example

```python
def calculate_signal_strength(self, data: pd.DataFrame,
                            window: int = 20) -> float:
    """Calculate signal strength using statistical measures.

    This function computes the signal strength based on recent
    price movements and volatility characteristics.

    Args:
        data: Historical price data as pandas DataFrame
        window: Rolling window size for calculations

    Returns:
        Signal strength as float between 0.0 and 1.0

    Raises:
        ValueError: If data is empty or window is invalid

    Example:
        >>> data = pd.DataFrame({'price': [100, 101, 102]})
        >>> strength = calculate_signal_strength(data, window=20)
        >>> print(f"Signal strength: {strength:.2f}")
        Signal strength: 0.75
    """
```

## Troubleshooting

### Common Issues

**Import errors during build:**
- Ensure all dependencies are installed
- Check Python path in `conf.py`
- Verify module structure matches imports

**Missing documentation:**
- Check docstring formatting
- Ensure modules are in `sys.path`
- Verify autosummary settings

**PDF build failures:**
- Install LaTeX distribution (MiKTeX/TeX Live)
- Check for missing LaTeX packages
- Use `--html` only if PDF fails

### Getting Help

- Check existing issues on GitHub
- Review Sphinx documentation: https://www.sphinx-doc.org/
- Test locally with `--verbose` flag

## License

This documentation is part of the Nautilus Trader Engine project and follows the same license terms.