"""
Environment Manager for Testing Framework

This module provides comprehensive environment setup and validation for the
Phase 1 testing framework, ensuring consistent and reliable test execution.
"""

import os
import sys
import subprocess
import venv
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import pkg_resources
import importlib.util
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Status enumeration for validation results"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class DependencyInfo:
    """Information about a package dependency"""
    name: str
    required_version: str
    installed_version: Optional[str] = None
    status: ValidationStatus = ValidationStatus.SKIPPED
    error_message: Optional[str] = None


@dataclass
class EnvironmentValidationResult:
    """Result of environment validation"""
    overall_status: ValidationStatus
    virtual_env_status: ValidationStatus
    dependencies_status: ValidationStatus
    python_version_status: ValidationStatus
    path_validation_status: ValidationStatus
    dependency_details: List[DependencyInfo]
    error_messages: List[str]
    warnings: List[str]
    validation_summary: Dict[str, Any]


@dataclass
class DependencyValidationResult:
    """Result of dependency validation"""
    total_dependencies: int
    validated_dependencies: int
    missing_dependencies: List[str]
    version_mismatches: List[DependencyInfo]
    status: ValidationStatus
    details: List[DependencyInfo]


class EnvironmentManager:
    """
    Manages testing environment setup and validation.
    
    This class handles virtual environment activation, dependency verification,
    and comprehensive environment validation for the testing framework.
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize the EnvironmentManager.
        
        Args:
            project_root: Path to the project root directory. If None, uses current directory.
        """
        self.project_root = project_root or Path.cwd()
        self.venv_path = self.project_root / ".venv"
        self.requirements_file = self.project_root / "requirements.txt"
        self.python_executable = self._get_python_executable()
        
    def _get_python_executable(self) -> Path:
        """Get the Python executable path for the virtual environment."""
        if os.name == 'nt':  # Windows
            return self.venv_path / "Scripts" / "python.exe"
        else:  # Unix-like systems
            return self.venv_path / "bin" / "python"
    
    def setup_virtual_environment(self) -> bool:
        """
        Setup and validate .venv environment.
        
        Returns:
            bool: True if virtual environment is successfully set up and validated.
        """
        try:
            logger.info("Setting up virtual environment...")
            
            # Check if virtual environment already exists
            if not self.venv_path.exists():
                logger.info(f"Creating virtual environment at {self.venv_path}")
                venv.create(self.venv_path, with_pip=True)
            
            # Validate virtual environment
            if not self._validate_virtual_environment():
                logger.error("Virtual environment validation failed")
                return False
            
            # Activate virtual environment
            if not self._activate_virtual_environment():
                logger.error("Failed to activate virtual environment")
                return False
            
            logger.info("Virtual environment setup completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup virtual environment: {str(e)}")
            return False
    
    def _validate_virtual_environment(self) -> bool:
        """
        Validate that the virtual environment is properly configured.
        
        Returns:
            bool: True if virtual environment is valid.
        """
        try:
            # Check if virtual environment directory exists
            if not self.venv_path.exists():
                logger.error(f"Virtual environment directory does not exist: {self.venv_path}")
                return False
            
            # Check if Python executable exists
            if not self.python_executable.exists():
                logger.error(f"Python executable not found: {self.python_executable}")
                return False
            
            # Check if pip is available
            pip_executable = self._get_pip_executable()
            if not pip_executable.exists():
                logger.error(f"Pip executable not found: {pip_executable}")
                return False
            
            # Test Python execution
            result = subprocess.run(
                [str(self.python_executable), "--version"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Python executable test failed: {result.stderr}")
                return False
            
            logger.info(f"Virtual environment validated: {result.stdout.strip()}")
            return True
            
        except Exception as e:
            logger.error(f"Virtual environment validation error: {str(e)}")
            return False
    
    def _get_pip_executable(self) -> Path:
        """Get the pip executable path for the virtual environment."""
        if os.name == 'nt':  # Windows
            return self.venv_path / "Scripts" / "pip.exe"
        else:  # Unix-like systems
            return self.venv_path / "bin" / "pip"
    
    def _activate_virtual_environment(self) -> bool:
        """
        Activate the virtual environment by modifying sys.path and environment variables.
        
        Returns:
            bool: True if activation is successful.
        """
        try:
            # Add virtual environment site-packages to sys.path
            site_packages = self._get_site_packages_path()
            if site_packages and site_packages.exists():
                if str(site_packages) not in sys.path:
                    sys.path.insert(0, str(site_packages))
            
            # Set environment variables
            os.environ['VIRTUAL_ENV'] = str(self.venv_path)
            os.environ['PATH'] = f"{self.venv_path / 'Scripts' if os.name == 'nt' else self.venv_path / 'bin'}{os.pathsep}{os.environ.get('PATH', '')}"
            
            # Update sys.executable
            sys.executable = str(self.python_executable)
            
            logger.info("Virtual environment activated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to activate virtual environment: {str(e)}")
            return False
    
    def _get_site_packages_path(self) -> Optional[Path]:
        """Get the site-packages path for the virtual environment."""
        if os.name == 'nt':  # Windows
            return self.venv_path / "Lib" / "site-packages"
        else:  # Unix-like systems
            # Find the correct Python version directory
            lib_path = self.venv_path / "lib"
            if lib_path.exists():
                for item in lib_path.iterdir():
                    if item.is_dir() and item.name.startswith("python"):
                        site_packages = item / "site-packages"
                        if site_packages.exists():
                            return site_packages
        return None
    
    def validate_dependencies(self) -> DependencyValidationResult:
        """
        Validate all requirements.txt dependencies.
        
        Returns:
            DependencyValidationResult: Comprehensive dependency validation results.
        """
        try:
            logger.info("Validating dependencies...")
            
            # Read requirements.txt
            if not self.requirements_file.exists():
                logger.error(f"Requirements file not found: {self.requirements_file}")
                return DependencyValidationResult(
                    total_dependencies=0,
                    validated_dependencies=0,
                    missing_dependencies=[],
                    version_mismatches=[],
                    status=ValidationStatus.FAILED,
                    details=[]
                )
            
            required_packages = self._parse_requirements_file()
            installed_packages = self._get_installed_packages()
            
            dependency_details = []
            missing_dependencies = []
            version_mismatches = []
            
            for package_name, required_version in required_packages.items():
                dependency_info = DependencyInfo(
                    name=package_name,
                    required_version=required_version
                )
                
                if package_name.lower() in installed_packages:
                    installed_version = installed_packages[package_name.lower()]
                    dependency_info.installed_version = installed_version
                    
                    # Version comparison
                    if self._compare_versions(installed_version, required_version):
                        dependency_info.status = ValidationStatus.PASSED
                    else:
                        dependency_info.status = ValidationStatus.FAILED
                        dependency_info.error_message = f"Version mismatch: required {required_version}, installed {installed_version}"
                        version_mismatches.append(dependency_info)
                else:
                    dependency_info.status = ValidationStatus.FAILED
                    dependency_info.error_message = "Package not installed"
                    missing_dependencies.append(package_name)
                
                dependency_details.append(dependency_info)
            
            # Determine overall status
            total_dependencies = len(required_packages)
            failed_dependencies = len(missing_dependencies) + len(version_mismatches)
            validated_dependencies = total_dependencies - failed_dependencies
            
            overall_status = ValidationStatus.PASSED if failed_dependencies == 0 else ValidationStatus.FAILED
            
            result = DependencyValidationResult(
                total_dependencies=total_dependencies,
                validated_dependencies=validated_dependencies,
                missing_dependencies=missing_dependencies,
                version_mismatches=version_mismatches,
                status=overall_status,
                details=dependency_details
            )
            
            logger.info(f"Dependency validation completed: {validated_dependencies}/{total_dependencies} passed")
            return result
            
        except Exception as e:
            logger.error(f"Dependency validation error: {str(e)}")
            return DependencyValidationResult(
                total_dependencies=0,
                validated_dependencies=0,
                missing_dependencies=[],
                version_mismatches=[],
                status=ValidationStatus.FAILED,
                details=[]
            )
    
    def _parse_requirements_file(self) -> Dict[str, str]:
        """
        Parse requirements.txt file and extract package names and versions.
        
        Returns:
            Dict[str, str]: Dictionary mapping package names to required versions.
        """
        packages = {}
        
        try:
            with open(self.requirements_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Skip -e (editable) installs and other pip options
                    if line.startswith('-'):
                        continue
                    
                    # Parse package specification
                    if '==' in line:
                        package_name, version = line.split('==', 1)
                        packages[package_name.strip().lower()] = version.strip()
                    elif '>=' in line:
                        package_name, version = line.split('>=', 1)
                        packages[package_name.strip().lower()] = f">={version.strip()}"
                    elif '<=' in line:
                        package_name, version = line.split('<=', 1)
                        packages[package_name.strip().lower()] = f"<={version.strip()}"
                    elif '>' in line:
                        package_name, version = line.split('>', 1)
                        packages[package_name.strip().lower()] = f">{version.strip()}"
                    elif '<' in line:
                        package_name, version = line.split('<', 1)
                        packages[package_name.strip().lower()] = f"<{version.strip()}"
                    else:
                        # No version specified
                        packages[line.strip().lower()] = "any"
        
        except Exception as e:
            logger.error(f"Error parsing requirements file: {str(e)}")
        
        return packages
    
    def _get_installed_packages(self) -> Dict[str, str]:
        """
        Get list of installed packages with versions.
        
        Returns:
            Dict[str, str]: Dictionary mapping package names to installed versions.
        """
        packages = {}
        
        try:
            # Use pip list to get installed packages
            result = subprocess.run(
                [str(self.python_executable), "-m", "pip", "list", "--format=json"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                import json
                package_list = json.loads(result.stdout)
                for package in package_list:
                    packages[package['name'].lower()] = package['version']
            else:
                logger.warning(f"Failed to get pip list: {result.stderr}")
                
                # Fallback: use pkg_resources
                for dist in pkg_resources.working_set:
                    packages[dist.project_name.lower()] = dist.version
        
        except Exception as e:
            logger.error(f"Error getting installed packages: {str(e)}")
            
            # Final fallback: use pkg_resources
            try:
                for dist in pkg_resources.working_set:
                    packages[dist.project_name.lower()] = dist.version
            except Exception as fallback_error:
                logger.error(f"Fallback method also failed: {str(fallback_error)}")
        
        return packages
    
    def _compare_versions(self, installed_version: str, required_version: str) -> bool:
        """
        Compare installed version with required version.
        
        Args:
            installed_version: The currently installed version
            required_version: The required version specification
            
        Returns:
            bool: True if the installed version satisfies the requirement
        """
        try:
            from packaging import version
            from packaging.specifiers import SpecifierSet
            
            if required_version == "any":
                return True
            
            # Handle exact version match
            if not any(op in required_version for op in ['>=', '<=', '>', '<', '!=']):
                return version.parse(installed_version) == version.parse(required_version)
            
            # Handle version specifiers
            spec = SpecifierSet(required_version)
            return version.parse(installed_version) in spec
            
        except Exception as e:
            logger.warning(f"Version comparison error for {installed_version} vs {required_version}: {str(e)}")
            # Fallback to string comparison for exact matches
            if required_version.startswith('=='):
                return installed_version == required_version.replace('==', '')
            else:
                # For other operators, we can't reliably compare without packaging
                logger.warning(f"Cannot compare versions without packaging library: {installed_version} vs {required_version}")
                return False
    
    def pip_list_comparison_and_validation(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Perform pip list comparison and comprehensive validation.
        
        Returns:
            Tuple[bool, Dict[str, Any]]: Success status and detailed comparison results
        """
        try:
            logger.info("Performing pip list comparison and validation...")
            
            # Get current pip list
            current_packages = self._get_installed_packages()
            
            # Get required packages
            required_packages = self._parse_requirements_file()
            
            # Perform comparison
            comparison_results = {
                'total_required': len(required_packages),
                'total_installed': len(current_packages),
                'matching_packages': [],
                'missing_packages': [],
                'extra_packages': [],
                'version_mismatches': [],
                'validation_details': []
            }
            
            # Check required packages
            for req_name, req_version in required_packages.items():
                if req_name in current_packages:
                    installed_version = current_packages[req_name]
                    if self._compare_versions(installed_version, req_version):
                        comparison_results['matching_packages'].append({
                            'name': req_name,
                            'required_version': req_version,
                            'installed_version': installed_version,
                            'status': 'match'
                        })
                    else:
                        comparison_results['version_mismatches'].append({
                            'name': req_name,
                            'required_version': req_version,
                            'installed_version': installed_version,
                            'status': 'version_mismatch'
                        })
                else:
                    comparison_results['missing_packages'].append({
                        'name': req_name,
                        'required_version': req_version,
                        'status': 'missing'
                    })
            
            # Check for extra packages (installed but not in requirements)
            for inst_name, inst_version in current_packages.items():
                if inst_name not in required_packages:
                    comparison_results['extra_packages'].append({
                        'name': inst_name,
                        'installed_version': inst_version,
                        'status': 'extra'
                    })
            
            # Calculate success status
            success = (len(comparison_results['missing_packages']) == 0 and 
                      len(comparison_results['version_mismatches']) == 0)
            
            # Add validation summary
            comparison_results['validation_summary'] = {
                'success': success,
                'missing_count': len(comparison_results['missing_packages']),
                'mismatch_count': len(comparison_results['version_mismatches']),
                'extra_count': len(comparison_results['extra_packages']),
                'match_count': len(comparison_results['matching_packages'])
            }
            
            logger.info(f"Pip list comparison completed. Success: {success}")
            return success, comparison_results
            
        except Exception as e:
            logger.error(f"Pip list comparison error: {str(e)}")
            return False, {'error': str(e)}
    
    def comprehensive_environment_validation(self) -> EnvironmentValidationResult:
        """
        Perform comprehensive environment validation.
        
        Returns:
            EnvironmentValidationResult: Complete validation results
        """
        logger.info("Starting comprehensive environment validation...")
        
        error_messages = []
        warnings = []
        
        # 1. Virtual environment validation
        venv_status = ValidationStatus.PASSED if self._validate_virtual_environment() else ValidationStatus.FAILED
        if venv_status == ValidationStatus.FAILED:
            error_messages.append("Virtual environment validation failed")
        
        # 2. Python version validation
        python_status = self._validate_python_version()
        if python_status == ValidationStatus.FAILED:
            error_messages.append("Python version validation failed")
        elif python_status == ValidationStatus.WARNING:
            warnings.append("Python version validation has warnings")
        
        # 3. Path validation
        path_status = self._validate_paths()
        if path_status == ValidationStatus.FAILED:
            error_messages.append("Path validation failed")
        
        # 4. Dependency validation
        dependency_result = self.validate_dependencies()
        dependencies_status = dependency_result.status
        if dependencies_status == ValidationStatus.FAILED:
            error_messages.append(f"Dependency validation failed: {len(dependency_result.missing_dependencies)} missing, {len(dependency_result.version_mismatches)} mismatched")
        
        # 5. Pip list comparison
        pip_success, pip_results = self.pip_list_comparison_and_validation()
        if not pip_success:
            error_messages.append("Pip list validation failed")
        
        # Determine overall status
        if error_messages:
            overall_status = ValidationStatus.FAILED
        elif warnings:
            overall_status = ValidationStatus.WARNING
        else:
            overall_status = ValidationStatus.PASSED
        
        # Create validation summary
        validation_summary = {
            'virtual_environment': venv_status.value,
            'python_version': python_status.value,
            'path_validation': path_status.value,
            'dependencies': dependencies_status.value,
            'pip_comparison': pip_success,
            'total_dependencies': dependency_result.total_dependencies,
            'validated_dependencies': dependency_result.validated_dependencies,
            'missing_dependencies': len(dependency_result.missing_dependencies),
            'version_mismatches': len(dependency_result.version_mismatches),
            'pip_results': pip_results
        }
        
        result = EnvironmentValidationResult(
            overall_status=overall_status,
            virtual_env_status=venv_status,
            dependencies_status=dependencies_status,
            python_version_status=python_status,
            path_validation_status=path_status,
            dependency_details=dependency_result.details,
            error_messages=error_messages,
            warnings=warnings,
            validation_summary=validation_summary
        )
        
        logger.info(f"Comprehensive environment validation completed. Overall status: {overall_status.value}")
        return result
    
    def _validate_python_version(self) -> ValidationStatus:
        """Validate Python version compatibility."""
        try:
            result = subprocess.run(
                [str(self.python_executable), "--version"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return ValidationStatus.FAILED
            
            version_str = result.stdout.strip()
            logger.info(f"Python version: {version_str}")
            
            # Extract version number
            import re
            version_match = re.search(r'Python (\d+)\.(\d+)\.(\d+)', version_str)
            if not version_match:
                return ValidationStatus.FAILED
            
            major, minor, patch = map(int, version_match.groups())
            
            # Check minimum Python version (3.8+)
            if major < 3 or (major == 3 and minor < 8):
                return ValidationStatus.FAILED
            
            # Warn for very new versions that might have compatibility issues
            if major > 3 or (major == 3 and minor > 11):
                return ValidationStatus.WARNING
            
            return ValidationStatus.PASSED
            
        except Exception as e:
            logger.error(f"Python version validation error: {str(e)}")
            return ValidationStatus.FAILED
    
    def _validate_paths(self) -> ValidationStatus:
        """Validate critical paths exist and are accessible."""
        try:
            critical_paths = [
                self.project_root,
                self.venv_path,
                self.requirements_file
            ]
            
            for path in critical_paths:
                if not path.exists():
                    logger.error(f"Critical path does not exist: {path}")
                    return ValidationStatus.FAILED
                
                # Check read permissions
                if not os.access(path, os.R_OK):
                    logger.error(f"No read access to critical path: {path}")
                    return ValidationStatus.FAILED
            
            return ValidationStatus.PASSED
            
        except Exception as e:
            logger.error(f"Path validation error: {str(e)}")
            return ValidationStatus.FAILED
    
    def install_missing_dependencies(self) -> bool:
        """
        Install missing dependencies from requirements.txt.
        
        Returns:
            bool: True if installation is successful
        """
        try:
            logger.info("Installing missing dependencies...")
            
            # First, upgrade pip
            subprocess.run(
                [str(self.python_executable), "-m", "pip", "install", "--upgrade", "pip"],
                check=True,
                timeout=300
            )
            
            # Install requirements
            result = subprocess.run(
                [str(self.python_executable), "-m", "pip", "install", "-r", str(self.requirements_file)],
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode == 0:
                logger.info("Dependencies installed successfully")
                return True
            else:
                logger.error(f"Failed to install dependencies: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error installing dependencies: {str(e)}")
            return False
    
    def generate_environment_report(self) -> str:
        """
        Generate a comprehensive environment validation report.
        
        Returns:
            str: Formatted environment report
        """
        validation_result = self.comprehensive_environment_validation()
        
        report_lines = [
            "=" * 80,
            "ENVIRONMENT VALIDATION REPORT",
            "=" * 80,
            f"Overall Status: {validation_result.overall_status.value.upper()}",
            f"Timestamp: {__import__('datetime').datetime.now().isoformat()}",
            "",
            "VALIDATION RESULTS:",
            f"  Virtual Environment: {validation_result.virtual_env_status.value}",
            f"  Python Version: {validation_result.python_version_status.value}",
            f"  Path Validation: {validation_result.path_validation_status.value}",
            f"  Dependencies: {validation_result.dependencies_status.value}",
            "",
            "DEPENDENCY DETAILS:",
            f"  Total Dependencies: {len(validation_result.dependency_details)}",
            f"  Passed: {sum(1 for d in validation_result.dependency_details if d.status == ValidationStatus.PASSED)}",
            f"  Failed: {sum(1 for d in validation_result.dependency_details if d.status == ValidationStatus.FAILED)}",
            ""
        ]
        
        if validation_result.error_messages:
            report_lines.extend([
                "ERRORS:",
                *[f"  - {error}" for error in validation_result.error_messages],
                ""
            ])
        
        if validation_result.warnings:
            report_lines.extend([
                "WARNINGS:",
                *[f"  - {warning}" for warning in validation_result.warnings],
                ""
            ])
        
        # Add failed dependencies details
        failed_deps = [d for d in validation_result.dependency_details if d.status == ValidationStatus.FAILED]
        if failed_deps:
            report_lines.extend([
                "FAILED DEPENDENCIES:",
                *[f"  - {dep.name}: {dep.error_message}" for dep in failed_deps],
                ""
            ])
        
        report_lines.extend([
            "VALIDATION SUMMARY:",
            *[f"  {key}: {value}" for key, value in validation_result.validation_summary.items()],
            "=" * 80
        ])
        
        return "\n".join(report_lines)