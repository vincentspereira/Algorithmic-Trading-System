"""
Auto-generated API Documentation System for Nautilus Trader Engine
Automatically generates comprehensive API documentation from codebase analysis.
"""

import inspect
import importlib
import pkgutil
import sys
import os
import ast
import re
from typing import Dict, List, Any, Optional, Tuple, Type, Union
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
import networkx as nx
import matplotlib.pyplot as plt
from jinja2 import Template

# Optional imports
try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

try:
    import graphviz
    GRAPHVIZ_AVAILABLE = True
except ImportError:
    GRAPHVIZ_AVAILABLE = False


@dataclass
class APIEndpoint:
    """Represents an API endpoint with full metadata."""
    name: str
    module: str
    class_name: Optional[str] = None
    function_name: Optional[str] = None
    signature: str = ""
    docstring: str = ""
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    return_type: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    complexity: str = "medium"
    stability: str = "stable"
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)


@dataclass
class ModuleDocumentation:
    """Documentation for a complete module."""
    name: str
    path: str
    classes: List[APIEndpoint] = field(default_factory=list)
    functions: List[APIEndpoint] = field(default_factory=list)
    constants: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    overview: str = ""
    examples: List[str] = field(default_factory=list)


@dataclass
class ProjectDocumentation:
    """Complete project documentation structure."""
    name: str
    version: str
    modules: List[ModuleDocumentation] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)
    coverage: float = 0.0
    total_endpoints: int = 0
    documented_endpoints: int = 0


class DocstringParser:
    """Advanced docstring parser with multiple format support."""

    def __init__(self):
        self.formats = {
            'google': self._parse_google_format,
            'numpy': self._parse_numpy_format,
            'sphinx': self._parse_sphinx_format,
            'plain': self._parse_plain_format
        }

    def parse(self, docstring: str) -> Dict[str, Any]:
        """Parse docstring and extract structured information."""
        if not docstring:
            return {}

        # Detect format
        format_type = self._detect_format(docstring)

        # Parse using appropriate format
        return self.formats[format_type](docstring)

    def _detect_format(self, docstring: str) -> str:
        """Detect docstring format."""
        lines = docstring.strip().split('\n')

        # Check for Google format
        if any('Args:' in line or 'Returns:' in line for line in lines):
            return 'google'

        # Check for NumPy format
        if any('Parameters' in line or 'Returns' in line for line in lines):
            return 'numpy'

        # Check for Sphinx format
        if any(':param' in line or ':returns:' in line for line in lines):
            return 'sphinx'

        return 'plain'

    def _parse_google_format(self, docstring: str) -> Dict[str, Any]:
        """Parse Google-style docstring."""
        result = {
            'description': '',
            'parameters': [],
            'returns': '',
            'raises': [],
            'examples': [],
            'notes': []
        }

        lines = docstring.strip().split('\n')
        current_section = 'description'
        current_param = None

        for line in lines:
            line = line.strip()

            if line.startswith('Args:') or line.startswith('Arguments:'):
                current_section = 'args'
                continue
            elif line.startswith('Returns:'):
                current_section = 'returns'
                continue
            elif line.startswith('Raises:'):
                current_section = 'raises'
                continue
            elif line.startswith('Examples:') or line.startswith('Example:'):
                current_section = 'examples'
                continue
            elif line.startswith('Notes:'):
                current_section = 'notes'
                continue

            if current_section == 'description':
                if not result['description']:
                    result['description'] = line
                else:
                    result['description'] += ' ' + line

            elif current_section == 'args':
                if line and not line.startswith(' ') and ':' in line:
                    param_name, param_desc = line.split(':', 1)
                    current_param = {
                        'name': param_name.strip(),
                        'type': 'Any',
                        'description': param_desc.strip()
                    }
                    result['parameters'].append(current_param)
                elif current_param is not None and line.startswith(' '):
                    if isinstance(current_param, dict) and 'description' in current_param:
                        current_param['description'] += ' ' + line.strip()

            elif current_section == 'returns':
                if line:
                    result['returns'] += line + ' '

            elif current_section == 'raises':
                if line:
                    result['raises'].append(line)

            elif current_section == 'examples':
                if line:
                    result['examples'].append(line)

            elif current_section == 'notes':
                if line:
                    result['notes'].append(line)

        # Clean up
        result['returns'] = result['returns'].strip()
        result['description'] = result['description'].strip()

        return result

    def _parse_numpy_format(self, docstring: str) -> Dict[str, Any]:
        """Parse NumPy-style docstring."""
        # Similar implementation to Google format but with NumPy conventions
        return self._parse_google_format(docstring)

    def _parse_sphinx_format(self, docstring: str) -> Dict[str, Any]:
        """Parse Sphinx-style docstring."""
        result = {
            'description': '',
            'parameters': [],
            'returns': '',
            'raises': [],
            'examples': [],
            'notes': []
        }

        lines = docstring.strip().split('\n')
        i = 0

        # Get description
        while i < len(lines) and not lines[i].strip().startswith(':'):
            if lines[i].strip():
                result['description'] += lines[i].strip() + ' '
            i += 1

        result['description'] = result['description'].strip()

        # Parse Sphinx directives
        while i < len(lines):
            line = lines[i].strip()

            if line.startswith(':param'):
                param_match = re.match(r':param\s+(\w+)\s*:\s*(.*)', line)
                if param_match:
                    param_name, param_desc = param_match.groups()
                    result['parameters'].append({
                        'name': param_name,
                        'type': 'Any',
                        'description': param_desc.strip()
                    })

            elif line.startswith(':returns:') or line.startswith(':rtype:'):
                if ':returns:' in line:
                    _, return_desc = line.split(':returns:', 1)
                    result['returns'] = return_desc.strip()
                i += 1
                continue

            elif line.startswith(':raises:'):
                _, raise_desc = line.split(':raises:', 1)
                result['raises'].append(raise_desc.strip())

            i += 1

        return result

    def _parse_plain_format(self, docstring: str) -> Dict[str, Any]:
        """Parse plain text docstring."""
        return {
            'description': docstring.strip(),
            'parameters': [],
            'returns': '',
            'raises': [],
            'examples': [],
            'notes': []
        }


class CodeAnalyzer:
    """Analyzes Python code to extract API information."""

    def __init__(self):
        self.docstring_parser = DocstringParser()

    def analyze_module(self, module_path: str) -> ModuleDocumentation:
        """Analyze a Python module and extract documentation."""
        module_name = self._get_module_name(module_path)

        try:
            # Import the module
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Analyze module contents
            classes = []
            functions = []
            constants = []

            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and obj.__module__ == module.__name__:
                    classes.append(self._analyze_class(obj, module_name))
                elif inspect.isfunction(obj) and obj.__module__ == module.__name__:
                    functions.append(self._analyze_function(obj, module_name))
                elif not name.startswith('_') and not callable(obj):
                    constants.append(self._analyze_constant(name, obj))

            # Get module docstring
            overview = ""
            if module.__doc__:
                parsed_doc = self.docstring_parser.parse(module.__doc__)
                overview = parsed_doc.get('description', '')

            return ModuleDocumentation(
                name=module_name,
                path=module_path,
                classes=classes,
                functions=functions,
                constants=constants,
                overview=overview
            )

        except Exception as e:
            print(f"Error analyzing module {module_path}: {e}")
            return ModuleDocumentation(name=module_name, path=module_path)

    def _analyze_class(self, cls: Type, module_name: str) -> APIEndpoint:
        """Analyze a class and extract documentation."""
        # Get class methods
        methods = []
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if not name.startswith('_') or name == '__init__':
                methods.append(self._analyze_method(method, cls.__name__, module_name))

        # Parse class docstring
        doc_info = {}
        if cls.__doc__:
            doc_info = self.docstring_parser.parse(cls.__doc__)

        return APIEndpoint(
            name=cls.__name__,
            module=module_name,
            class_name=cls.__name__,
            docstring=doc_info.get('description', ''),
            parameters=[],  # Class parameters would be in __init__
            examples=doc_info.get('examples', []),
            tags=['class']
        )

    def _analyze_function(self, func, module_name: str) -> APIEndpoint:
        """Analyze a function and extract documentation."""
        return self._analyze_callable(func, module_name, function_name=func.__name__)

    def _analyze_method(self, method, class_name: str, module_name: str) -> APIEndpoint:
        """Analyze a method and extract documentation."""
        return self._analyze_callable(method, module_name,
                                     class_name=class_name,
                                     function_name=method.__name__)

    def _analyze_callable(self, callable_obj, module_name: str,
                         class_name: str = None, function_name: str = None) -> APIEndpoint:
        """Analyze a callable (function/method) and extract documentation."""
        try:
            # Get signature
            sig = inspect.signature(callable_obj)
            signature = str(sig)

            # Parse parameters
            parameters = []
            for param_name, param in sig.parameters.items():
                param_info = {
                    'name': param_name,
                    'type': str(param.annotation) if param.annotation != param.empty else 'Any',
                    'default': str(param.default) if param.default != param.empty else None,
                    'description': ''
                }
                parameters.append(param_info)

            # Get return type
            return_type = str(sig.return_annotation) if sig.return_annotation != sig.empty else None

            # Parse docstring
            doc_info = {}
            if callable_obj.__doc__:
                doc_info = self.docstring_parser.parse(callable_obj.__doc__)

                # Update parameter descriptions
                if 'parameters' in doc_info:
                    param_dict = {p['name']: p for p in parameters}
                    for doc_param in doc_info['parameters']:
                        if doc_param['name'] in param_dict:
                            param_dict[doc_param['name']]['description'] = doc_param['description']

            # Get decorators
            decorators = []
            if hasattr(callable_obj, '__wrapped__'):
                # Function is decorated
                decorators.append("decorated")

            return APIEndpoint(
                name=function_name or callable_obj.__name__,
                module=module_name,
                class_name=class_name,
                function_name=function_name or callable_obj.__name__,
                signature=signature,
                docstring=doc_info.get('description', ''),
                parameters=parameters,
                return_type=return_type,
                decorators=decorators,
                examples=doc_info.get('examples', []),
                tags=['function', 'method'] if class_name else ['function']
            )

        except Exception as e:
            print(f"Error analyzing callable {callable_obj}: {e}")
            return APIEndpoint(
                name=function_name or str(callable_obj),
                module=module_name,
                class_name=class_name,
                function_name=function_name
            )

    def _analyze_constant(self, name: str, value: Any) -> Dict[str, Any]:
        """Analyze a constant."""
        return {
            'name': name,
            'value': str(value),
            'type': type(value).__name__
        }

    def _get_module_name(self, module_path: str) -> str:
        """Extract module name from file path."""
        path = Path(module_path)
        if path.name == '__init__.py':
            return str(path.parent.name)
        else:
            return path.stem


class DependencyAnalyzer:
    """Analyzes code dependencies and relationships."""

    def __init__(self):
        self.graph = nx.DiGraph()

    def analyze_file(self, file_path: str) -> Dict[str, List[str]]:
        """Analyze a Python file for dependencies."""
        dependencies = {
            'imports': [],
            'classes': [],
            'functions': []
        }

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse AST
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        dependencies['imports'].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        dependencies['imports'].append(node.module)
                elif isinstance(node, ast.ClassDef):
                    dependencies['classes'].append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    dependencies['functions'].append(node.name)

        except Exception as e:
            print(f"Error analyzing dependencies in {file_path}: {e}")

        return dependencies

    def build_dependency_graph(self, modules: List[ModuleDocumentation]) -> nx.DiGraph:
        """Build a dependency graph from modules."""
        for module in modules:
            self.graph.add_node(module.name, type='module')

            # Add dependencies
            for dep in module.dependencies:
                self.graph.add_edge(module.name, dep, type='dependency')

        return self.graph

    def get_circular_dependencies(self) -> List[List[str]]:
        """Find circular dependencies in the graph."""
        try:
            cycles = list(nx.simple_cycles(self.graph))
            return cycles
        except:
            return []


class DocumentationGenerator:
    """Generates documentation in various formats."""

    def __init__(self):
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, Template]:
        """Load Jinja2 templates for documentation generation."""
        templates = {}

        # HTML template
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ project.name }} API Documentation</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .module { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
                .endpoint { margin: 10px 0; padding: 10px; background-color: #f9f9f9; border-radius: 3px; }
                .signature { font-family: monospace; background-color: #f0f0f0; padding: 5px; margin: 5px 0; }
                .parameters { margin-left: 20px; }
                .parameter { margin: 5px 0; }
                .description { margin: 10px 0; }
                .tags { margin: 5px 0; }
                .tag { display: inline-block; background-color: #e0e0e0; padding: 2px 5px; margin: 2px; border-radius: 3px; font-size: 0.8em; }
            </style>
        </head>
        <body>
            <h1>{{ project.name }} API Documentation</h1>
            <p>Version: {{ project.version }}</p>
            <p>Generated: {{ project.generated_at.strftime('%Y-%m-%d %H:%M:%S') }}</p>
            <p>Coverage: {{ "%.1f"|format(project.coverage) }}%</p>

            {% for module in project.modules %}
            <div class="module">
                <h2>{{ module.name }}</h2>
                <p class="description">{{ module.overview }}</p>

                {% if module.classes %}
                <h3>Classes</h3>
                {% for cls in module.classes %}
                <div class="endpoint">
                    <h4>{{ cls.name }}</h4>
                    <div class="description">{{ cls.docstring }}</div>
                    <div class="tags">
                        {% for tag in cls.tags %}
                        <span class="tag">{{ tag }}</span>
                        {% endfor %}
                    </div>
                </div>
                {% endfor %}
                {% endif %}

                {% if module.functions %}
                <h3>Functions</h3>
                {% for func in module.functions %}
                <div class="endpoint">
                    <h4>{{ func.name }}</h4>
                    <div class="signature">{{ func.signature }}</div>
                    <div class="description">{{ func.docstring }}</div>

                    {% if func.parameters %}
                    <div class="parameters">
                        <strong>Parameters:</strong>
                        {% for param in func.parameters %}
                        <div class="parameter">
                            <code>{{ param.name }}</code> ({{ param.type }}):
                            {{ param.description }}
                        </div>
                        {% endfor %}
                    </div>
                    {% endif %}

                    {% if func.return_type %}
                    <div><strong>Returns:</strong> {{ func.return_type }}</div>
                    {% endif %}

                    <div class="tags">
                        {% for tag in func.tags %}
                        <span class="tag">{{ tag }}</span>
                        {% endfor %}
                    </div>
                </div>
                {% endfor %}
                {% endif %}
            </div>
            {% endfor %}
        </body>
        </html>
        """

        templates['html'] = Template(html_template)
        return templates

    def generate_html(self, project: ProjectDocumentation) -> str:
        """Generate HTML documentation."""
        return self.templates['html'].render(project=project)

    def generate_markdown(self, project: ProjectDocumentation) -> str:
        """Generate Markdown documentation."""
        lines = []

        lines.append(f"# {project.name} API Documentation")
        lines.append("")
        lines.append(f"**Version:** {project.version}")
        lines.append(f"**Generated:** {project.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Coverage:** {project.coverage:.1f}%")
        lines.append("")

        for module in project.modules:
            lines.append(f"## {module.name}")
            lines.append("")
            if module.overview:
                lines.append(module.overview)
                lines.append("")

            if module.classes:
                lines.append("### Classes")
                lines.append("")
                for cls in module.classes:
                    lines.append(f"#### {cls.name}")
                    lines.append("")
                    if cls.docstring:
                        lines.append(cls.docstring)
                        lines.append("")
                    if cls.tags:
                        lines.append(f"**Tags:** {', '.join(cls.tags)}")
                        lines.append("")

            if module.functions:
                lines.append("### Functions")
                lines.append("")
                for func in module.functions:
                    lines.append(f"#### {func.name}")
                    lines.append("")
                    lines.append(f"```python")
                    lines.append(f"{func.signature}")
                    lines.append("```")
                    lines.append("")
                    if func.docstring:
                        lines.append(func.docstring)
                        lines.append("")
                    if func.parameters:
                        lines.append("**Parameters:**")
                        lines.append("")
                        for param in func.parameters:
                            lines.append(f"- `{param['name']}` ({param['type']}): {param['description']}")
                        lines.append("")
                    if func.return_type:
                        lines.append(f"**Returns:** {func.return_type}")
                        lines.append("")
                    if func.tags:
                        lines.append(f"**Tags:** {', '.join(func.tags)}")
                        lines.append("")

        return "\n".join(lines)

    def generate_json(self, project: ProjectDocumentation) -> str:
        """Generate JSON documentation."""
        def serialize_obj(obj):
            if hasattr(obj, '__dict__'):
                return obj.__dict__
            elif isinstance(obj, datetime):
                return obj.isoformat()
            else:
                return str(obj)

        # Convert to serializable format
        data = {
            'name': project.name,
            'version': project.version,
            'generated_at': project.generated_at.isoformat(),
            'coverage': project.coverage,
            'total_endpoints': project.total_endpoints,
            'documented_endpoints': project.documented_endpoints,
            'modules': []
        }

        for module in project.modules:
            module_data = {
                'name': module.name,
                'path': module.path,
                'overview': module.overview,
                'classes': [serialize_obj(cls) for cls in module.classes],
                'functions': [serialize_obj(func) for func in module.functions],
                'constants': module.constants,
                'dependencies': module.dependencies
            }
            data['modules'].append(module_data)

        return json.dumps(data, indent=2)


class APIDocumentationGenerator:
    """Main API documentation generator."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.code_analyzer = CodeAnalyzer()
        self.dependency_analyzer = DependencyAnalyzer()
        self.doc_generator = DocumentationGenerator()

    def generate_documentation(self, output_dir: str = "docs/api",
                             formats: List[str] = None) -> ProjectDocumentation:
        """Generate complete API documentation."""
        if formats is None:
            formats = ['html', 'markdown', 'json']

        # Discover Python modules
        modules = self._discover_modules()

        # Analyze modules
        module_docs = []
        for module_path in modules:
            try:
                module_doc = self.code_analyzer.analyze_module(str(module_path))
                module_docs.append(module_doc)
            except Exception as e:
                print(f"Failed to analyze module {module_path}: {e}")

        # Build dependency graph
        dependency_graph = self.dependency_analyzer.build_dependency_graph(module_docs)

        # Create project documentation
        project = ProjectDocumentation(
            name="Nautilus Trader Engine",
            version="1.0.0",
            modules=module_docs
        )

        # Calculate coverage
        total_endpoints = sum(len(m.classes) + len(m.functions) for m in module_docs)
        documented_endpoints = sum(
            len([c for c in m.classes if c.docstring]) +
            len([f for f in m.functions if f.docstring])
            for m in module_docs
        )

        project.total_endpoints = total_endpoints
        project.documented_endpoints = documented_endpoints
        project.coverage = (documented_endpoints / total_endpoints * 100) if total_endpoints > 0 else 0

        # Generate documentation in requested formats
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for format_type in formats:
            content = ""
            file_path = None

            try:
                if format_type == 'html':
                    content = self.doc_generator.generate_html(project)
                    file_path = output_path / "api_documentation.html"
                elif format_type == 'markdown':
                    content = self.doc_generator.generate_markdown(project)
                    file_path = output_path / "api_documentation.md"
                elif format_type == 'json':
                    content = self.doc_generator.generate_json(project)
                    file_path = output_path / "api_documentation.json"

                if file_path and content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)

                    print(f"Generated {format_type} documentation: {file_path}")

            except Exception as e:
                print(f"Failed to generate {format_type} documentation: {e}")

        return project

    def _discover_modules(self) -> List[Path]:
        """Discover all Python modules in the project."""
        modules = []

        # Walk through all Python files
        for root, dirs, files in os.walk(self.project_root):
            # Skip certain directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'tests', 'docs']]

            for file in files:
                if file.endswith('.py') and not file.startswith('test_'):
                    modules.append(Path(root) / file)

        return modules

    def generate_dependency_graph(self, output_file: str = "docs/dependency_graph.png"):
        """Generate a visual dependency graph."""
        try:
            # Create dependency graph
            pos = nx.spring_layout(self.dependency_analyzer.graph)
            plt.figure(figsize=(12, 8))

            # Draw the graph
            nx.draw(self.dependency_analyzer.graph, pos, with_labels=True,
                   node_color='lightblue', node_size=500, font_size=8,
                   font_weight='bold', edge_color='gray', arrows=True)

            plt.title("Nautilus Trader Engine Dependency Graph")
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            plt.close()

            print(f"Generated dependency graph: {output_file}")

        except Exception as e:
            print(f"Failed to generate dependency graph: {e}")


def main():
    """Main entry point for documentation generation."""
    import argparse

    parser = argparse.ArgumentParser(description='Generate API documentation')
    parser.add_argument('--project-root', default='.',
                       help='Project root directory')
    parser.add_argument('--output-dir', default='docs/api',
                       help='Output directory for documentation')
    parser.add_argument('--formats', nargs='+',
                       choices=['html', 'markdown', 'json'],
                       default=['html', 'markdown', 'json'],
                       help='Documentation formats to generate')
    parser.add_argument('--dependency-graph', action='store_true',
                       help='Generate dependency graph visualization')

    args = parser.parse_args()

    # Generate documentation
    generator = APIDocumentationGenerator(args.project_root)
    project = generator.generate_documentation(args.output_dir, args.formats)

    print("\nDocumentation Summary:")
    print(f"  Modules analyzed: {len(project.modules)}")
    print(f"  Total endpoints: {project.total_endpoints}")
    print(f"  Documented endpoints: {project.documented_endpoints}")
    print(f"  Coverage: {project.coverage:.1f}%")

    if args.dependency_graph:
        generator.generate_dependency_graph()


if __name__ == "__main__":
    main()