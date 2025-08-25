"""Tests for documentation utilities"""

import unittest
import tempfile
import json
from pathlib import Path
from textwrap import dedent
from dependency_management.documentation.doc_utils import (
    DocumentationValidator,
    APIDocumentationGenerator,
    DocumentationIssue
)

class TestDocumentationValidator(unittest.TestCase):
    def setUp(self):
        self.validator = DocumentationValidator()
        self.temp_dir = tempfile.mkdtemp()
        
    def _create_test_file(self, content: str) -> str:
        """Create a temporary Python file with given content"""
        path = Path(self.temp_dir) / "test_file.py"
        path.write_text(content)
        return str(path)
        
    def test_validate_missing_module_docstring(self):
        """Test detection of missing module docstring"""
        content = dedent("""
            def test_function():
                pass
        """)
        
        file_path = self._create_test_file(content)
        issues = self.validator.validate_file(file_path)
        
        self.assertTrue(any(
            i.issue_type == 'missing_docstring' and i.line_number == 1
            for i in issues
        ))
        
    def test_validate_missing_function_docstring(self):
        """Test detection of missing function docstring"""
        content = dedent('''
            """Module docstring"""
            
            def test_function():
                pass
        ''')
        
        file_path = self._create_test_file(content)
        issues = self.validator.validate_file(file_path)
        
        self.assertTrue(any(
            i.issue_type == 'missing_docstring' and 'test_function' in i.message
            for i in issues
        ))
        
    def test_validate_missing_class_docstring(self):
        """Test detection of missing class docstring"""
        content = dedent('''
            """Module docstring"""
            
            class TestClass:
                def method(self):
                    """Method docstring"""
                    pass
        ''')
        
        file_path = self._create_test_file(content)
        issues = self.validator.validate_file(file_path)
        
        self.assertTrue(any(
            i.issue_type == 'missing_docstring' and 'TestClass' in i.message
            for i in issues
        ))
        
    def test_validate_missing_parameter_documentation(self):
        """Test detection of missing parameter documentation"""
        content = dedent('''
            """Module docstring"""
            
            def test_function(param1, param2):
                """Function docstring
                
                Args:
                    param1: First parameter
                """
                pass
        ''')
        
        file_path = self._create_test_file(content)
        issues = self.validator.validate_file(file_path)
        
        self.assertTrue(any(
            i.issue_type == 'missing_param_doc' and 'param2' in i.message
            for i in issues
        ))
        
    def test_validate_extra_parameter_documentation(self):
        """Test detection of extra parameter documentation"""
        content = dedent('''
            """Module docstring"""
            
            def test_function(param1):
                """Function docstring
                
                Args:
                    param1: First parameter
                    param2: Non-existent parameter
                """
                pass
        ''')
        
        file_path = self._create_test_file(content)
        issues = self.validator.validate_file(file_path)
        
        self.assertTrue(any(
            i.issue_type == 'extra_param_doc' and 'param2' in i.message
            for i in issues
        ))
        
class TestAPIDocumentationGenerator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / "project"
        self.project_dir.mkdir()
        
    def _create_test_module(self, name: str, content: str) -> None:
        """Create a test module in the project directory"""
        module_path = self.project_dir / f"{name}.py"
        module_path.write_text(dedent(content))
        
    def test_generate_markdown_documentation(self):
        """Test markdown documentation generation"""
        # Create test module
        self._create_test_module("test_module", '''
            """Test module docstring"""
            
            class TestClass:
                """Test class docstring"""
                
                def test_method(self, param1: str, param2: int = 0) -> bool:
                    """Test method docstring
                    
                    Args:
                        param1: First parameter
                        param2: Second parameter
                        
                    Returns:
                        bool: Result value
                    """
                    return True
        ''')
        
        # Generate documentation
        output_file = self.project_dir / "api_docs.md"
        generator = APIDocumentationGenerator(str(self.project_dir))
        generator.generate_markdown(str(output_file))
        
        # Verify documentation content
        content = output_file.read_text()
        
        self.assertIn("# API Documentation", content)
        self.assertIn("## test_module", content)
        self.assertIn("Test module docstring", content)
        self.assertIn("### class TestClass", content)
        self.assertIn("Test class docstring", content)
        self.assertIn("test_method(param1: str, param2: int = 0) -> bool", content)
        self.assertIn("Test method docstring", content)
        
    def test_generate_documentation_with_inheritance(self):
        """Test documentation generation with class inheritance"""
        self._create_test_module("inheritance", '''
            """Module with inheritance"""
            
            class BaseClass:
                """Base class"""
                pass
                
            class DerivedClass(BaseClass):
                """Derived class"""
                pass
        ''')
        
        output_file = self.project_dir / "api_docs.md"
        generator = APIDocumentationGenerator(str(self.project_dir))
        generator.generate_markdown(str(output_file))
        
        content = output_file.read_text()
        
        self.assertIn("### class BaseClass", content)
        self.assertIn("### class DerivedClass(BaseClass)", content)
        
    def test_generate_documentation_with_type_annotations(self):
        """Test documentation generation with type annotations"""
        self._create_test_module("annotations", '''
            """Module with type annotations"""
            
            from typing import List, Dict, Optional
            
            def test_function(
                param1: List[str],
                param2: Dict[str, int],
                param3: Optional[bool] = None
            ) -> List[Dict[str, Any]]:
                """Function with type annotations"""
                pass
        ''')
        
        output_file = self.project_dir / "api_docs.md"
        generator = APIDocumentationGenerator(str(self.project_dir))
        generator.generate_markdown(str(output_file))
        
        content = output_file.read_text()
        
        self.assertIn("List[str]", content)
        self.assertIn("Dict[str, int]", content)
        self.assertIn("Optional[bool]", content)
        self.assertIn("List[Dict[str, Any]]", content)
        
if __name__ == '__main__':
    unittest.main()
