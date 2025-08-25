"""
Documentation utilities for generating and validating documentation.
"""

import ast
import inspect
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Type
from dataclasses import dataclass
from docstring_parser import parse as parse_docstring

@dataclass
class DocumentationIssue:
    """Represents a documentation issue found during validation"""
    file_path: str
    line_number: int
    issue_type: str
    message: str
    severity: str  # 'error', 'warning', 'info'

class DocumentationValidator:
    """Validates Python documentation against best practices"""
    
    def __init__(self):
        self.issues: List[DocumentationIssue] = []
        
    def validate_file(self, file_path: str) -> List[DocumentationIssue]:
        """Validate documentation in a Python file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            self.issues = []
            
            # Validate module docstring
            self._validate_module_docstring(tree, file_path)
            
            # Validate classes and functions
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    self._validate_class(node, file_path)
                elif isinstance(node, ast.FunctionDef):
                    self._validate_function(node, file_path)
                    
            return self.issues
        except Exception as e:
            self.issues.append(DocumentationIssue(
                file_path=file_path,
                line_number=1,
                issue_type='error',
                message=f"Failed to parse file: {str(e)}",
                severity='error'
            ))
            return self.issues
            
    def _validate_module_docstring(self, tree: ast.Module, file_path: str) -> None:
        """Validate module-level docstring"""
        if not ast.get_docstring(tree):
            self.issues.append(DocumentationIssue(
                file_path=file_path,
                line_number=1,
                issue_type='missing_docstring',
                message="Module is missing a docstring",
                severity='warning'
            ))
            
    def _validate_class(self, node: ast.ClassDef, file_path: str) -> None:
        """Validate class documentation"""
        # Check for docstring
        if not ast.get_docstring(node):
            self.issues.append(DocumentationIssue(
                file_path=file_path,
                line_number=node.lineno,
                issue_type='missing_docstring',
                message=f"Class '{node.name}' is missing a docstring",
                severity='warning'
            ))
            return
            
        docstring = parse_docstring(ast.get_docstring(node))
        
        # Check for class attributes documentation
        for child in node.body:
            if isinstance(child, ast.AnnAssign) and child.simple:
                attr_name = child.target.id
                if not any(p.arg_name == attr_name for p in docstring.params):
                    self.issues.append(DocumentationIssue(
                        file_path=file_path,
                        line_number=child.lineno,
                        issue_type='missing_attribute_doc',
                        message=f"Class attribute '{attr_name}' is not documented",
                        severity='info'
                    ))
                    
    def _validate_function(self, node: ast.FunctionDef, file_path: str) -> None:
        """Validate function documentation"""
        # Check for docstring
        if not ast.get_docstring(node):
            self.issues.append(DocumentationIssue(
                file_path=file_path,
                line_number=node.lineno,
                issue_type='missing_docstring',
                message=f"Function '{node.name}' is missing a docstring",
                severity='warning'
            ))
            return
            
        docstring = parse_docstring(ast.get_docstring(node))
        
        # Check parameters
        arg_names = {a.arg for a in node.args.args if a.arg != 'self'}
        doc_params = {p.arg_name for p in docstring.params}
        
        # Missing parameter documentation
        for arg in arg_names - doc_params:
            self.issues.append(DocumentationIssue(
                file_path=file_path,
                line_number=node.lineno,
                issue_type='missing_param_doc',
                message=f"Parameter '{arg}' is not documented",
                severity='warning'
            ))
            
        # Extra parameter documentation
        for param in doc_params - arg_names:
            self.issues.append(DocumentationIssue(
                file_path=file_path,
                line_number=node.lineno,
                issue_type='extra_param_doc',
                message=f"Documentation for non-existent parameter '{param}'",
                severity='warning'
            ))
            
        # Check return annotation and documentation
        if node.returns and not docstring.returns:
            self.issues.append(DocumentationIssue(
                file_path=file_path,
                line_number=node.lineno,
                issue_type='missing_return_doc',
                message="Return value is not documented",
                severity='warning'
            ))

class APIDocumentationGenerator:
    """Generates API documentation from Python code"""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        
    def generate_markdown(self, output_file: str) -> None:
        """Generate Markdown documentation for the entire API"""
        content = []
        
        # Add header
        content.append("# API Documentation\n")
        content.append("## Table of Contents\n")
        
        # Generate documentation for each Python file
        for py_file in self.base_path.rglob("*.py"):
            if py_file.name.startswith("test_"):
                continue
                
            rel_path = py_file.relative_to(self.base_path)
            module_name = str(rel_path).replace("/", ".").replace(".py", "")
            
            # Add to table of contents
            content.append(f"- [{module_name}](#{module_name.replace('.', '')})\n")
            
        content.append("\n")
        
        # Generate detailed documentation
        for py_file in self.base_path.rglob("*.py"):
            if py_file.name.startswith("test_"):
                continue
                
            content.extend(self._document_file(py_file))
            
        # Write documentation
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("".join(content))
            
    def _document_file(self, file_path: Path) -> List[str]:
        """Generate documentation for a single Python file"""
        content = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
                
            rel_path = file_path.relative_to(self.base_path)
            module_name = str(rel_path).replace("/", ".").replace(".py", "")
            
            content.append(f"\n## {module_name}\n\n")
            
            # Module docstring
            if docstring := ast.get_docstring(tree):
                content.append(f"{docstring}\n\n")
                
            # Document classes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    content.extend(self._document_class(node))
                elif isinstance(node, ast.FunctionDef) and node.parent_field == tree.body:
                    content.extend(self._document_function(node))
                    
        except Exception as e:
            content.append(f"Error processing {file_path}: {str(e)}\n\n")
            
        return content
        
    def _document_class(self, node: ast.ClassDef) -> List[str]:
        """Generate documentation for a class"""
        content = []
        
        # Class definition
        bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
        if bases:
            content.append(f"### class {node.name}({', '.join(bases)})\n\n")
        else:
            content.append(f"### class {node.name}\n\n")
            
        # Class docstring
        if docstring := ast.get_docstring(node):
            content.append(f"{docstring}\n\n")
            
        # Document methods
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                content.extend(self._document_function(child, is_method=True))
                
        return content
        
    def _document_function(self, node: ast.FunctionDef, is_method: bool = False) -> List[str]:
        """Generate documentation for a function or method"""
        content = []
        
        # Function signature
        args = []
        for arg in node.args.args:
            if is_method and arg.arg == 'self':
                continue
            if annotation := arg.annotation:
                args.append(f"{arg.arg}: {self._format_annotation(annotation)}")
            else:
                args.append(arg.arg)
                
        if node.returns:
            return_anno = f" -> {self._format_annotation(node.returns)}"
        else:
            return_anno = ""
            
        prefix = "#### " if is_method else "### "
        content.append(f"{prefix}{node.name}({', '.join(args)}){return_anno}\n\n")
        
        # Function docstring
        if docstring := ast.get_docstring(node):
            content.append(f"{docstring}\n\n")
            
        return content
        
    def _format_annotation(self, node: ast.AST) -> str:
        """Format type annotation AST node as string"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Subscript):
            return f"{node.value.id}[{self._format_annotation(node.slice)}]"
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        else:
            return ast.unparse(node)

def validate_project_documentation(project_path: str) -> List[DocumentationIssue]:
    """Validate documentation for an entire project"""
    validator = DocumentationValidator()
    issues = []
    
    for py_file in Path(project_path).rglob("*.py"):
        if not py_file.name.startswith("test_"):
            issues.extend(validator.validate_file(str(py_file)))
            
    return issues

def generate_project_documentation(
    project_path: str,
    output_file: str
) -> None:
    """Generate API documentation for an entire project"""
    generator = APIDocumentationGenerator(project_path)
    generator.generate_markdown(output_file)
