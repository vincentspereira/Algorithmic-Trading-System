"""
API Versioning and Backward Compatibility System
Provides comprehensive API versioning with backward compatibility,
deprecation management, and migration tools.
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable, Type
from dataclasses import dataclass, field, asdict
from enum import Enum
import inspect
from functools import wraps
import warnings

try:
    from flask import Flask, request, jsonify, g
    from flask_restx import Api, Resource, fields
    FLASK_AVAILABLE = True
except ImportError:
    Flask = None
    Api = None
    Resource = None
    fields = None
    FLASK_AVAILABLE = False

class VersioningStrategy(Enum):
    """API versioning strategies"""
    URL_PATH = "url_path"          # /api/v1/resource
    QUERY_PARAM = "query_param"    # /api/resource?version=v1
    HEADER = "header"              # Accept: application/vnd.api.v1+json
    CONTENT_TYPE = "content_type"  # Content-Type: application/vnd.api.v1+json

class DeprecationLevel(Enum):
    """Deprecation levels"""
    NONE = "none"
    SOFT = "soft"        # Warning only
    HARD = "hard"        # Error response
    SUNSET = "sunset"    # Scheduled removal

@dataclass
class APIVersion:
    """API version definition"""
    version: str
    release_date: datetime
    deprecation_date: Optional[datetime] = None
    sunset_date: Optional[datetime] = None
    deprecation_level: DeprecationLevel = DeprecationLevel.NONE
    changelog: List[str] = field(default_factory=list)
    breaking_changes: List[str] = field(default_factory=list)
    migration_guide: str = ""
    is_default: bool = False
    is_supported: bool = True

@dataclass
class FieldMapping:
    """Field mapping for version compatibility"""
    old_field: str
    new_field: str
    transformer: Optional[Callable] = None
    reverse_transformer: Optional[Callable] = None
    deprecated_in: Optional[str] = None
    removed_in: Optional[str] = None

@dataclass
class EndpointMapping:
    """Endpoint mapping for version compatibility"""
    old_path: str
    new_path: str
    old_method: str
    new_method: str
    parameter_mappings: List[FieldMapping] = field(default_factory=list)
    response_mappings: List[FieldMapping] = field(default_factory=list)
    deprecated_in: Optional[str] = None
    removed_in: Optional[str] = None

@dataclass
class VersionCompatibility:
    """Version compatibility configuration"""
    source_version: str
    target_version: str
    field_mappings: List[FieldMapping] = field(default_factory=list)
    endpoint_mappings: List[EndpointMapping] = field(default_factory=list)
    custom_transformers: Dict[str, Callable] = field(default_factory=dict)

class VersionManager:
    """API version management system"""
    
    def __init__(self, default_strategy: VersioningStrategy = VersioningStrategy.URL_PATH):
        self.default_strategy = default_strategy
        self.versions: Dict[str, APIVersion] = {}
        self.compatibility_rules: List[VersionCompatibility] = []
        self.logger = logging.getLogger(__name__)
        
        # Initialize default versions
        self._initialize_default_versions()
    
    def _initialize_default_versions(self):
        """Initialize default API versions"""
        # Version 1.0
        v1 = APIVersion(
            version="v1",
            release_date=datetime(2024, 1, 1),
            is_default=True,
            changelog=[
                "Initial API release",
                "Basic trading operations",
                "Portfolio management",
                "Market data access"
            ]
        )
        self.add_version(v1)
        
        # Version 2.0
        v2 = APIVersion(
            version="v2",
            release_date=datetime(2024, 6, 1),
            changelog=[
                "Enhanced order management",
                "Real-time WebSocket support",
                "Advanced analytics endpoints",
                "Improved error handling"
            ],
            breaking_changes=[
                "Order status field renamed from 'state' to 'status'",
                "Timestamp format changed to ISO 8601",
                "Pagination parameters restructured"
            ]
        )
        self.add_version(v2)
        
        # Version 3.0
        v3 = APIVersion(
            version="v3",
            release_date=datetime(2024, 12, 1),
            changelog=[
                "GraphQL support",
                "Batch operations",
                "Enhanced security",
                "Performance improvements"
            ],
            breaking_changes=[
                "Authentication method changed to OAuth 2.0",
                "Response format standardized",
                "Deprecated endpoints removed"
            ]
        )
        self.add_version(v3)
    
    def add_version(self, version: APIVersion):
        """Add new API version"""
        self.versions[version.version] = version
        self.logger.info(f"Added API version {version.version}")
    
    def deprecate_version(self, version: str, deprecation_date: datetime = None,
                         sunset_date: datetime = None, level: DeprecationLevel = DeprecationLevel.SOFT):
        """Deprecate API version"""
        if version not in self.versions:
            raise ValueError(f"Version {version} not found")
        
        api_version = self.versions[version]
        api_version.deprecation_date = deprecation_date or datetime.now()
        api_version.sunset_date = sunset_date
        api_version.deprecation_level = level
        
        self.logger.info(f"Deprecated API version {version} with level {level.value}")
    
    def add_compatibility_rule(self, rule: VersionCompatibility):
        """Add version compatibility rule"""
        self.compatibility_rules.append(rule)
        self.logger.info(f"Added compatibility rule: {rule.source_version} -> {rule.target_version}")
    
    def get_version_from_request(self, request, strategy: VersioningStrategy = None) -> str:
        """Extract version from request based on strategy"""
        strategy = strategy or self.default_strategy
        
        if strategy == VersioningStrategy.URL_PATH:
            # Extract from URL path like /api/v2/resource
            path_parts = request.path.split('/')
            for part in path_parts:
                if part.startswith('v') and part[1:].replace('.', '').isdigit():
                    return part
        
        elif strategy == VersioningStrategy.QUERY_PARAM:
            # Extract from query parameter
            return request.args.get('version', self._get_default_version())
        
        elif strategy == VersioningStrategy.HEADER:
            # Extract from Accept header
            accept_header = request.headers.get('Accept', '')
            if 'application/vnd.api.' in accept_header:
                # Parse application/vnd.api.v2+json
                parts = accept_header.split('.')
                for part in parts:
                    if part.startswith('v') and '+' in part:
                        return part.split('+')[0]
        
        elif strategy == VersioningStrategy.CONTENT_TYPE:
            # Extract from Content-Type header
            content_type = request.headers.get('Content-Type', '')
            if 'application/vnd.api.' in content_type:
                parts = content_type.split('.')
                for part in parts:
                    if part.startswith('v') and '+' in part:
                        return part.split('+')[0]
        
        return self._get_default_version()
    
    def _get_default_version(self) -> str:
        """Get default API version"""
        for version, api_version in self.versions.items():
            if api_version.is_default:
                return version
        
        # Return latest version if no default set
        return max(self.versions.keys())
    
    def is_version_supported(self, version: str) -> bool:
        """Check if version is supported"""
        api_version = self.versions.get(version)
        if not api_version:
            return False
        
        return api_version.is_supported and api_version.deprecation_level != DeprecationLevel.SUNSET
    
    def get_deprecation_info(self, version: str) -> Optional[Dict[str, Any]]:
        """Get deprecation information for version"""
        api_version = self.versions.get(version)
        if not api_version or api_version.deprecation_level == DeprecationLevel.NONE:
            return None
        
        return {
            'version': version,
            'deprecation_level': api_version.deprecation_level.value,
            'deprecation_date': api_version.deprecation_date.isoformat() if api_version.deprecation_date else None,
            'sunset_date': api_version.sunset_date.isoformat() if api_version.sunset_date else None,
            'migration_guide': api_version.migration_guide,
            'latest_version': self._get_latest_version()
        }
    
    def _get_latest_version(self) -> str:
        """Get latest API version"""
        latest_date = datetime.min
        latest_version = None
        
        for version, api_version in self.versions.items():
            if api_version.release_date > latest_date and api_version.is_supported:
                latest_date = api_version.release_date
                latest_version = version
        
        return latest_version or self._get_default_version()

class DataTransformer:
    """Data transformation for version compatibility"""
    
    def __init__(self, version_manager: VersionManager):
        self.version_manager = version_manager
        self.logger = logging.getLogger(__name__)
    
    def transform_request(self, data: Dict[str, Any], source_version: str, target_version: str) -> Dict[str, Any]:
        """Transform request data between versions"""
        if source_version == target_version:
            return data.copy()  # Return a copy even for same version
        
        compatibility_rule = self._find_compatibility_rule(source_version, target_version)
        if not compatibility_rule:
            self.logger.warning(f"No compatibility rule found for {source_version} -> {target_version}")
            return data
        
        transformed_data = data.copy()
        
        # Apply field mappings
        for mapping in compatibility_rule.field_mappings:
            if mapping.old_field in transformed_data:
                value = transformed_data.pop(mapping.old_field)
                
                # Apply transformer if available
                if mapping.transformer:
                    try:
                        value = mapping.transformer(value)
                    except Exception as e:
                        self.logger.error(f"Error applying transformer for {mapping.old_field}: {e}")
                
                transformed_data[mapping.new_field] = value
        
        # Apply custom transformers
        for field, transformer in compatibility_rule.custom_transformers.items():
            if field in transformed_data:
                try:
                    transformed_data[field] = transformer(transformed_data[field])
                except Exception as e:
                    self.logger.error(f"Error applying custom transformer for {field}: {e}")
        
        return transformed_data
    
    def transform_response(self, data: Dict[str, Any], source_version: str, target_version: str) -> Dict[str, Any]:
        """Transform response data between versions"""
        if source_version == target_version:
            return data
        
        compatibility_rule = self._find_compatibility_rule(target_version, source_version)
        if not compatibility_rule:
            self.logger.warning(f"No compatibility rule found for {target_version} -> {source_version}")
            return data
        
        transformed_data = data.copy()
        
        # Apply reverse field mappings
        for mapping in compatibility_rule.field_mappings:
            if mapping.new_field in transformed_data:
                value = transformed_data.pop(mapping.new_field)
                
                # Apply reverse transformer if available
                if mapping.reverse_transformer:
                    try:
                        value = mapping.reverse_transformer(value)
                    except Exception as e:
                        self.logger.error(f"Error applying reverse transformer for {mapping.new_field}: {e}")
                
                transformed_data[mapping.old_field] = value
        
        return transformed_data
    
    def _find_compatibility_rule(self, source_version: str, target_version: str) -> Optional[VersionCompatibility]:
        """Find compatibility rule for version transformation"""
        for rule in self.version_manager.compatibility_rules:
            if rule.source_version == source_version and rule.target_version == target_version:
                return rule
        return None

class VersionedResource:
    """Base class for versioned API resources"""
    
    def __init__(self, version_manager: VersionManager, data_transformer: DataTransformer):
        self.version_manager = version_manager
        self.data_transformer = data_transformer
        self.logger = logging.getLogger(__name__)
    
    def handle_request(self, request, handler: Callable, target_version: str = None):
        """Handle versioned request"""
        # Get requested version
        requested_version = self.version_manager.get_version_from_request(request)
        target_version = target_version or self._get_handler_version(handler)
        
        # Check if version is supported
        if not self.version_manager.is_version_supported(requested_version):
            return self._unsupported_version_response(requested_version)
        
        # Check for deprecation
        deprecation_info = self.version_manager.get_deprecation_info(requested_version)
        if deprecation_info and deprecation_info['deprecation_level'] == 'hard':
            return self._deprecated_version_response(deprecation_info)
        
        # Transform request data if needed
        request_data = request.get_json() or {}
        if requested_version != target_version:
            request_data = self.data_transformer.transform_request(
                request_data, requested_version, target_version
            )
        
        # Call handler
        try:
            response_data = handler(request_data)
        except Exception as e:
            self.logger.error(f"Error in handler: {e}")
            return self._error_response(str(e))
        
        # Transform response data if needed
        if requested_version != target_version:
            response_data = self.data_transformer.transform_response(
                response_data, target_version, requested_version
            )
        
        # Create response
        response = jsonify(response_data)
        
        # Add version headers
        response.headers['X-API-Version'] = requested_version
        response.headers['X-API-Latest-Version'] = self.version_manager._get_latest_version()
        
        # Add deprecation headers if needed
        if deprecation_info:
            response.headers['X-API-Deprecation-Level'] = deprecation_info['deprecation_level']
            if deprecation_info['sunset_date']:
                response.headers['X-API-Sunset-Date'] = deprecation_info['sunset_date']
            response.headers['X-API-Migration-Guide'] = deprecation_info['migration_guide']
        
        return response
    
    def _get_handler_version(self, handler: Callable) -> str:
        """Get version that handler expects"""
        # Check for version annotation
        if hasattr(handler, '__version__'):
            return handler.__version__
        
        # Default to latest version
        return self.version_manager._get_latest_version()
    
    def _unsupported_version_response(self, version: str):
        """Return unsupported version response"""
        return jsonify({
            'error': {
                'code': 400,
                'name': 'Unsupported API Version',
                'description': f'API version {version} is not supported'
            },
            'supported_versions': list(self.version_manager.versions.keys()),
            'latest_version': self.version_manager._get_latest_version()
        }), 400
    
    def _deprecated_version_response(self, deprecation_info: Dict[str, Any]):
        """Return deprecated version response"""
        return jsonify({
            'error': {
                'code': 410,
                'name': 'API Version Deprecated',
                'description': f'API version {deprecation_info["version"]} is deprecated'
            },
            'deprecation_info': deprecation_info
        }), 410
    
    def _error_response(self, message: str):
        """Return error response"""
        return jsonify({
            'error': {
                'code': 500,
                'name': 'Internal Server Error',
                'description': message
            }
        }), 500

def versioned_endpoint(version: str = None, deprecated_in: str = None, removed_in: str = None):
    """Decorator for versioned endpoints"""
    def decorator(func):
        func.__version__ = version
        func.__deprecated_in__ = deprecated_in
        func.__removed_in__ = removed_in
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Add deprecation warning if needed
            if deprecated_in:
                warnings.warn(
                    f"Endpoint {func.__name__} is deprecated since version {deprecated_in}",
                    DeprecationWarning,
                    stacklevel=2
                )
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

def create_version_manager(strategy: VersioningStrategy = VersioningStrategy.URL_PATH) -> VersionManager:
    """Create version manager instance"""
    return VersionManager(default_strategy=strategy)

def create_data_transformer(version_manager: VersionManager) -> DataTransformer:
    """Create data transformer instance"""
    return DataTransformer(version_manager)

# Example compatibility rules
def setup_default_compatibility_rules(version_manager: VersionManager):
    """Setup default compatibility rules between versions"""
    
    # v1 to v2 compatibility
    v1_to_v2 = VersionCompatibility(
        source_version="v1",
        target_version="v2",
        field_mappings=[
            FieldMapping(
                old_field="state",
                new_field="status",
                transformer=lambda x: x.lower(),
                reverse_transformer=lambda x: x.upper()
            ),
            FieldMapping(
                old_field="created",
                new_field="created_at",
                transformer=lambda x: datetime.fromisoformat(x).isoformat() if isinstance(x, str) else x,
                reverse_transformer=lambda x: x
            )
        ],
        custom_transformers={
            "timestamp": lambda x: datetime.fromisoformat(x).isoformat() if isinstance(x, str) else x
        }
    )
    version_manager.add_compatibility_rule(v1_to_v2)
    
    # v2 to v3 compatibility
    v2_to_v3 = VersionCompatibility(
        source_version="v2",
        target_version="v3",
        field_mappings=[
            FieldMapping(
                old_field="order_id",
                new_field="id",
                transformer=lambda x: x,
                reverse_transformer=lambda x: x
            )
        ]
    )
    version_manager.add_compatibility_rule(v2_to_v3)

if __name__ == "__main__":
    # Example usage
    version_manager = create_version_manager(VersioningStrategy.URL_PATH)
    data_transformer = create_data_transformer(version_manager)
    
    # Setup compatibility rules
    setup_default_compatibility_rules(version_manager)
    
    # Deprecate v1
    version_manager.deprecate_version(
        "v1",
        deprecation_date=datetime.now(),
        sunset_date=datetime.now() + timedelta(days=365),
        level=DeprecationLevel.SOFT
    )
    
    print("Version manager initialized with:")
    for version, api_version in version_manager.versions.items():
        print(f"- {version}: {api_version.deprecation_level.value}")
    
    print(f"Compatibility rules: {len(version_manager.compatibility_rules)}")
    
    # Test data transformation
    v1_data = {
        "state": "ACTIVE",
        "created": "2024-01-15T10:30:00",
        "order_id": "12345"
    }
    
    v2_data = data_transformer.transform_request(v1_data, "v1", "v2")
    print(f"Transformed v1 -> v2: {v1_data} -> {v2_data}")
    
    v1_back = data_transformer.transform_response(v2_data, "v2", "v1")
    print(f"Transformed v2 -> v1: {v2_data} -> {v1_back}")