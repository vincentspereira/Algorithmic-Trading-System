"""
Test suite for EnvironmentManager class

This module contains comprehensive tests for the EnvironmentManager class,
validating all functionality including virtual environment management,
dependency validation, and environment setup.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
import subprocess

# Add the framework directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from environment_manager import (
    EnvironmentManager,
    ValidationStatus,
    DependencyInfo,
    EnvironmentValidationResult,
    DependencyValidationResult
)


class TestEnvironmentManager:
    """Test suite for EnvironmentManager class"""
    
    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory for testing"""
        temp_dir = Path(tempfile.mkdtemp())
        
        # Create a sample requirements.txt
        requirements_content = """
pytest==7.4.0
requests>=2.28.0
numpy==1.24.3
pandas>=1.5.0,<2.0.0
# This is a comment
flask==2.3.2
"""
        (temp_dir / "requirements.txt").write_text(requirements_content.strip())
        
        yield temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def env_manager(self, temp_project_dir):
        """Create an EnvironmentManager instance for testing"""
        return EnvironmentManager(project_root=temp_project_dir)
    
    def test_init(self, temp_project_dir):
        """Test EnvironmentManager initialization"""
        env_manager = EnvironmentManager(project_root=temp_project_dir)
        
        assert env_manager.project_root == temp_project_dir
        assert env_manager.venv_path == temp_project_dir / ".venv"
        assert env_manager.requirements_file == temp_project_dir / "requirements.txt"
        assert env_manager.python_executable is not None
    
    def test_init_default_project_root(self):
        """Test EnvironmentManager initialization with default project root"""
        env_manager = EnvironmentManager()
        
        assert env_manager.project_root == Path.cwd()
        assert env_manager.venv_path == Path.cwd() / ".venv"
    
    def test_get_python_executable_windows(self, env_manager):
        """Test Python executable path on Windows"""
        with patch('os.name', 'nt'):
            env_manager = EnvironmentManager(env_manager.project_root)
            expected_path = env_manager.venv_path / "Scripts" / "python.exe"
            assert env_manager.python_executable == expected_path
    
    def test_get_python_executable_unix(self, env_manager):
        """Test Python executable path on Unix-like systems"""
        with patch('os.name', 'posix'):
            env_manager = EnvironmentManager(env_manager.project_root)
            expected_path = env_manager.venv_path / "bin" / "python"
            assert env_manager.python_executable == expected_path
    
    def test_parse_requirements_file(self, env_manager):
        """Test parsing of requirements.txt file"""
        packages = env_manager._parse_requirements_file()
        
        expected_packages = {
            'pytest': '7.4.0',
            'requests': '>=2.28.0',
            'numpy': '1.24.3',
            'pandas': '>=1.5.0,<2.0.0',
            'flask': '2.3.2'
        }
        
        assert packages == expected_packages
    
    def test_parse_requirements_file_missing(self, temp_project_dir):
        """Test parsing when requirements.txt is missing"""
        # Remove requirements.txt
        (temp_project_dir / "requirements.txt").unlink()
        
        env_manager = EnvironmentManager(project_root=temp_project_dir)
        packages = env_manager._parse_requirements_file()
        
        assert packages == {}
    
    @patch('subprocess.run')
    def test_get_installed_packages_pip_success(self, mock_run, env_manager):
        """Test getting installed packages via pip list (success case)"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = '''[
            {"name": "pytest", "version": "7.4.0"},
            {"name": "requests", "version": "2.28.1"},
            {"name": "numpy", "version": "1.24.3"}
        ]'''
        mock_run.return_value = mock_result
        
        packages = env_manager._get_installed_packages()
        
        expected_packages = {
            'pytest': '7.4.0',
            'requests': '2.28.1',
            'numpy': '1.24.3'
        }
        
        assert packages == expected_packages
    
    @patch('subprocess.run')
    @patch('pkg_resources.working_set')
    def test_get_installed_packages_pip_failure_fallback(self, mock_working_set, mock_run, env_manager):
        """Test getting installed packages when pip fails (fallback to pkg_resources)"""
        # Mock pip failure
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "pip error"
        mock_run.return_value = mock_result
        
        # Mock pkg_resources
        mock_dist1 = Mock()
        mock_dist1.project_name = "pytest"
        mock_dist1.version = "7.4.0"
        
        mock_dist2 = Mock()
        mock_dist2.project_name = "requests"
        mock_dist2.version = "2.28.1"
        
        mock_working_set.__iter__ = Mock(return_value=iter([mock_dist1, mock_dist2]))
        
        packages = env_manager._get_installed_packages()
        
        expected_packages = {
            'pytest': '7.4.0',
            'requests': '2.28.1'
        }
        
        assert packages == expected_packages
    
    def test_compare_versions_exact_match(self, env_manager):
        """Test version comparison for exact matches"""
        assert env_manager._compare_versions("1.0.0", "1.0.0") == True
        assert env_manager._compare_versions("1.0.0", "1.0.1") == False
        assert env_manager._compare_versions("1.0.1", "1.0.0") == False
    
    def test_compare_versions_any(self, env_manager):
        """Test version comparison for 'any' requirement"""
        assert env_manager._compare_versions("1.0.0", "any") == True
        assert env_manager._compare_versions("2.5.3", "any") == True
    
    @patch('packaging.version')
    @patch('packaging.specifiers.SpecifierSet')
    def test_compare_versions_specifiers(self, mock_specifier_set, mock_version, env_manager):
        """Test version comparison with version specifiers"""
        # Mock the version parsing
        mock_version.parse.side_effect = lambda v: Mock(spec=v)
        
        # Mock the specifier set
        mock_spec = Mock()
        mock_spec.__contains__ = Mock(return_value=True)
        mock_specifier_set.return_value = mock_spec
        
        result = env_manager._compare_versions("2.28.1", ">=2.28.0")
        assert result == True
    
    def test_compare_versions_fallback(self, env_manager):
        """Test version comparison fallback when packaging is not available"""
        # Create a mock that raises ImportError for packaging imports
        original_import = __builtins__['__import__']
        
        def mock_import(name, *args, **kwargs):
            if name == 'packaging':
                raise ImportError("No module named 'packaging'")
            return original_import(name, *args, **kwargs)
        
        with patch('builtins.__import__', side_effect=mock_import):
            # Should fall back to string comparison for exact matches
            assert env_manager._compare_versions("1.0.0", "==1.0.0") == True
            assert env_manager._compare_versions("1.0.0", "==1.0.1") == False
            # Should return False for complex version specs without packaging
            assert env_manager._compare_versions("1.0.0", ">=1.0.0") == False
    
    @patch.object(EnvironmentManager, '_get_installed_packages')
    def test_validate_dependencies_success(self, mock_get_installed, env_manager):
        """Test successful dependency validation"""
        mock_get_installed.return_value = {
            'pytest': '7.4.0',
            'requests': '2.28.1',
            'numpy': '1.24.3',
            'pandas': '1.5.2',
            'flask': '2.3.2'
        }
        
        result = env_manager.validate_dependencies()
        
        assert result.status == ValidationStatus.PASSED
        assert result.total_dependencies == 5
        assert result.validated_dependencies == 5
        assert len(result.missing_dependencies) == 0
        assert len(result.version_mismatches) == 0
    
    @patch.object(EnvironmentManager, '_get_installed_packages')
    def test_validate_dependencies_missing_packages(self, mock_get_installed, env_manager):
        """Test dependency validation with missing packages"""
        mock_get_installed.return_value = {
            'pytest': '7.4.0',
            'requests': '2.28.1',
            # numpy and pandas missing
            'flask': '2.3.2'
        }
        
        result = env_manager.validate_dependencies()
        
        assert result.status == ValidationStatus.FAILED
        assert result.total_dependencies == 5
        assert result.validated_dependencies == 3
        assert len(result.missing_dependencies) == 2
        assert 'numpy' in result.missing_dependencies
        assert 'pandas' in result.missing_dependencies
    
    @patch.object(EnvironmentManager, '_get_installed_packages')
    def test_validate_dependencies_version_mismatch(self, mock_get_installed, env_manager):
        """Test dependency validation with version mismatches"""
        mock_get_installed.return_value = {
            'pytest': '7.3.0',  # Version mismatch
            'requests': '2.28.1',
            'numpy': '1.24.3',
            'pandas': '1.5.2',
            'flask': '2.2.0'  # Version mismatch
        }
        
        result = env_manager.validate_dependencies()
        
        assert result.status == ValidationStatus.FAILED
        assert len(result.version_mismatches) == 2
        
        # Check that version mismatches are properly identified
        mismatch_names = [dep.name for dep in result.version_mismatches]
        assert 'pytest' in mismatch_names
        assert 'flask' in mismatch_names
    
    def test_validate_dependencies_no_requirements_file(self, temp_project_dir):
        """Test dependency validation when requirements.txt doesn't exist"""
        # Remove requirements.txt
        (temp_project_dir / "requirements.txt").unlink()
        
        env_manager = EnvironmentManager(project_root=temp_project_dir)
        result = env_manager.validate_dependencies()
        
        assert result.status == ValidationStatus.FAILED
        assert result.total_dependencies == 0
    
    @patch.object(EnvironmentManager, '_get_installed_packages')
    def test_pip_list_comparison_and_validation_success(self, mock_get_installed, env_manager):
        """Test successful pip list comparison"""
        mock_get_installed.return_value = {
            'pytest': '7.4.0',
            'requests': '2.28.1',
            'numpy': '1.24.3',
            'pandas': '1.5.2',
            'flask': '2.3.2',
            'extra-package': '1.0.0'  # Extra package not in requirements
        }
        
        success, results = env_manager.pip_list_comparison_and_validation()
        
        assert success == True
        assert results['total_required'] == 5
        assert results['total_installed'] == 6
        assert len(results['matching_packages']) == 5
        assert len(results['missing_packages']) == 0
        assert len(results['version_mismatches']) == 0
        assert len(results['extra_packages']) == 1
        assert results['extra_packages'][0]['name'] == 'extra-package'
    
    @patch.object(EnvironmentManager, '_get_installed_packages')
    def test_pip_list_comparison_with_issues(self, mock_get_installed, env_manager):
        """Test pip list comparison with missing and mismatched packages"""
        mock_get_installed.return_value = {
            'pytest': '7.3.0',  # Version mismatch
            'requests': '2.28.1',
            # numpy missing
            'pandas': '1.5.2',
            'flask': '2.3.2'
        }
        
        success, results = env_manager.pip_list_comparison_and_validation()
        
        assert success == False
        assert len(results['missing_packages']) == 1
        assert results['missing_packages'][0]['name'] == 'numpy'
        assert len(results['version_mismatches']) == 1
        assert results['version_mismatches'][0]['name'] == 'pytest'
    
    @patch('subprocess.run')
    def test_validate_virtual_environment_success(self, mock_run, env_manager):
        """Test successful virtual environment validation"""
        # Create mock venv directory structure
        env_manager.venv_path.mkdir(parents=True, exist_ok=True)
        env_manager.python_executable.parent.mkdir(parents=True, exist_ok=True)
        env_manager.python_executable.touch()
        
        # Create pip executable
        pip_executable = env_manager._get_pip_executable()
        pip_executable.parent.mkdir(parents=True, exist_ok=True)
        pip_executable.touch()
        
        # Mock successful subprocess call
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Python 3.9.0"
        mock_run.return_value = mock_result
        
        result = env_manager._validate_virtual_environment()
        assert result == True
    
    def test_validate_virtual_environment_missing_venv(self, env_manager):
        """Test virtual environment validation when .venv doesn't exist"""
        result = env_manager._validate_virtual_environment()
        assert result == False
    
    @patch('subprocess.run')
    def test_validate_python_version_success(self, mock_run, env_manager):
        """Test successful Python version validation"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Python 3.9.7"
        mock_run.return_value = mock_result
        
        result = env_manager._validate_python_version()
        assert result == ValidationStatus.PASSED
    
    @patch('subprocess.run')
    def test_validate_python_version_too_old(self, mock_run, env_manager):
        """Test Python version validation with too old version"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Python 3.7.0"
        mock_run.return_value = mock_result
        
        result = env_manager._validate_python_version()
        assert result == ValidationStatus.FAILED
    
    @patch('subprocess.run')
    def test_validate_python_version_too_new(self, mock_run, env_manager):
        """Test Python version validation with very new version (warning)"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Python 3.12.0"
        mock_run.return_value = mock_result
        
        result = env_manager._validate_python_version()
        assert result == ValidationStatus.WARNING
    
    def test_validate_paths_success(self, env_manager):
        """Test successful path validation"""
        # Ensure all required paths exist
        env_manager.project_root.mkdir(parents=True, exist_ok=True)
        env_manager.venv_path.mkdir(parents=True, exist_ok=True)
        env_manager.requirements_file.touch()
        
        result = env_manager._validate_paths()
        assert result == ValidationStatus.PASSED
    
    def test_validate_paths_missing_requirements(self, env_manager):
        """Test path validation when requirements.txt is missing"""
        # Remove requirements.txt
        if env_manager.requirements_file.exists():
            env_manager.requirements_file.unlink()
        
        result = env_manager._validate_paths()
        assert result == ValidationStatus.FAILED
    
    @patch('subprocess.run')
    def test_install_missing_dependencies_success(self, mock_run, env_manager):
        """Test successful installation of missing dependencies"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = env_manager.install_missing_dependencies()
        assert result == True
        
        # Verify pip upgrade and install commands were called
        assert mock_run.call_count == 2
    
    @patch('subprocess.run')
    def test_install_missing_dependencies_failure(self, mock_run, env_manager):
        """Test failed installation of missing dependencies"""
        # First call (pip upgrade) succeeds, second call (install) fails
        mock_run.side_effect = [
            Mock(returncode=0),  # pip upgrade success
            Mock(returncode=1, stderr="Installation failed")  # install failure
        ]
        
        result = env_manager.install_missing_dependencies()
        assert result == False
    
    @patch.object(EnvironmentManager, '_validate_virtual_environment')
    @patch.object(EnvironmentManager, '_validate_python_version')
    @patch.object(EnvironmentManager, '_validate_paths')
    @patch.object(EnvironmentManager, 'validate_dependencies')
    @patch.object(EnvironmentManager, 'pip_list_comparison_and_validation')
    def test_comprehensive_environment_validation_success(
        self, mock_pip_comparison, mock_validate_deps, mock_validate_paths,
        mock_validate_python, mock_validate_venv, env_manager
    ):
        """Test successful comprehensive environment validation"""
        # Mock all validation methods to return success
        mock_validate_venv.return_value = True
        mock_validate_python.return_value = ValidationStatus.PASSED
        mock_validate_paths.return_value = ValidationStatus.PASSED
        
        mock_dep_result = DependencyValidationResult(
            total_dependencies=5,
            validated_dependencies=5,
            missing_dependencies=[],
            version_mismatches=[],
            status=ValidationStatus.PASSED,
            details=[]
        )
        mock_validate_deps.return_value = mock_dep_result
        
        mock_pip_comparison.return_value = (True, {'success': True})
        
        result = env_manager.comprehensive_environment_validation()
        
        assert result.overall_status == ValidationStatus.PASSED
        assert result.virtual_env_status == ValidationStatus.PASSED
        assert result.python_version_status == ValidationStatus.PASSED
        assert result.path_validation_status == ValidationStatus.PASSED
        assert result.dependencies_status == ValidationStatus.PASSED
        assert len(result.error_messages) == 0
        assert len(result.warnings) == 0
    
    @patch.object(EnvironmentManager, '_validate_virtual_environment')
    @patch.object(EnvironmentManager, '_validate_python_version')
    @patch.object(EnvironmentManager, '_validate_paths')
    @patch.object(EnvironmentManager, 'validate_dependencies')
    @patch.object(EnvironmentManager, 'pip_list_comparison_and_validation')
    def test_comprehensive_environment_validation_with_failures(
        self, mock_pip_comparison, mock_validate_deps, mock_validate_paths,
        mock_validate_python, mock_validate_venv, env_manager
    ):
        """Test comprehensive environment validation with failures"""
        # Mock some validation methods to return failures
        mock_validate_venv.return_value = False
        mock_validate_python.return_value = ValidationStatus.FAILED
        mock_validate_paths.return_value = ValidationStatus.PASSED
        
        mock_dep_result = DependencyValidationResult(
            total_dependencies=5,
            validated_dependencies=3,
            missing_dependencies=['numpy', 'pandas'],
            version_mismatches=[],
            status=ValidationStatus.FAILED,
            details=[]
        )
        mock_validate_deps.return_value = mock_dep_result
        
        mock_pip_comparison.return_value = (False, {'success': False})
        
        result = env_manager.comprehensive_environment_validation()
        
        assert result.overall_status == ValidationStatus.FAILED
        assert result.virtual_env_status == ValidationStatus.FAILED
        assert result.python_version_status == ValidationStatus.FAILED
        assert len(result.error_messages) > 0
    
    @patch.object(EnvironmentManager, 'comprehensive_environment_validation')
    def test_generate_environment_report(self, mock_validation, env_manager):
        """Test environment report generation"""
        # Mock validation result
        mock_result = EnvironmentValidationResult(
            overall_status=ValidationStatus.PASSED,
            virtual_env_status=ValidationStatus.PASSED,
            dependencies_status=ValidationStatus.PASSED,
            python_version_status=ValidationStatus.PASSED,
            path_validation_status=ValidationStatus.PASSED,
            dependency_details=[
                DependencyInfo(name="pytest", required_version="7.4.0", 
                             installed_version="7.4.0", status=ValidationStatus.PASSED)
            ],
            error_messages=[],
            warnings=[],
            validation_summary={'test': 'value'}
        )
        mock_validation.return_value = mock_result
        
        report = env_manager.generate_environment_report()
        
        assert "ENVIRONMENT VALIDATION REPORT" in report
        assert "Overall Status: PASSED" in report
        assert "VALIDATION RESULTS:" in report
        assert "DEPENDENCY DETAILS:" in report
        assert "VALIDATION SUMMARY:" in report
    
    def test_setup_virtual_environment_integration(self, env_manager):
        """Integration test for virtual environment setup"""
        # This test requires actual venv creation, so we'll mock the critical parts
        with patch('venv.create') as mock_create:
            with patch.object(env_manager, '_validate_virtual_environment', return_value=True):
                with patch.object(env_manager, '_activate_virtual_environment', return_value=True):
                    result = env_manager.setup_virtual_environment()
                    assert result == True
                    mock_create.assert_called_once()


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])