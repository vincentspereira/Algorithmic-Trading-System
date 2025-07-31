"""
OpenAPI 3.0 Specification Generator
Generates comprehensive OpenAPI specifications with automatic documentation,
schema validation, and interactive API explorer.
"""
import logging
import json
import yaml
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Type
from dataclasses import dataclass, field, asdict
from enum import Enum
import inspect
from pathlib import Path

try:
    from flask import Flask, request, jsonify, render_template_string
    from flask_restx import Api, Resource, fields, Model
    from marshmallow import Schema, fields as ma_fields
    FLASK_AVAILABLE = True
except ImportError:
    Flask = None
    Api = None
    Resource = None
    fields = None
    Model = None
    Schema = None
    ma_fields = None
    FLASK_AVAILABLE = False

class ParameterLocation(Enum):
    """Parameter location in request"""
    QUERY = "query"
    PATH = "path"
    HEADER = "header"
    COOKIE = "cookie"

class DataType(Enum):
    """OpenAPI data types"""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"

@dataclass
class OpenAPIParameter:
    """OpenAPI parameter definition"""
    name: str
    location: ParameterLocation
    data_type: DataType
    description: str = ""
    required: bool = False
    default: Any = None
    example: Any = None
    enum: List[Any] = field(default_factory=list)
    format: Optional[str] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    pattern: Optional[str] = None

@dataclass
class OpenAPIResponse:
    """OpenAPI response definition"""
    status_code: int
    description: str
    schema: Optional[Dict[str, Any]] = None
    examples: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, Dict[str, Any]] = field(default_factory=dict)

@dataclass
class OpenAPIEndpoint:
    """OpenAPI endpoint definition"""
    path: str
    method: str
    summary: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    parameters: List[OpenAPIParameter] = field(default_factory=list)
    request_body: Optional[Dict[str, Any]] = None
    responses: List[OpenAPIResponse] = field(default_factory=list)
    security: List[Dict[str, List[str]]] = field(default_factory=list)
    deprecated: bool = False
    operation_id: Optional[str] = None

@dataclass
class OpenAPISchema:
    """OpenAPI schema definition"""
    name: str
    schema_type: DataType
    properties: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)
    description: str = ""
    example: Optional[Dict[str, Any]] = None
    additional_properties: bool = True

class OpenAPIGenerator:
    """OpenAPI 3.0 specification generator"""
    
    def __init__(self, title: str = "API", version: str = "1.0.0", description: str = ""):
        self.title = title
        self.version = version
        self.description = description
        self.logger = logging.getLogger(__name__)
        
        # Storage for API components
        self.endpoints: List[OpenAPIEndpoint] = []
        self.schemas: Dict[str, OpenAPISchema] = {}
        self.security_schemes: Dict[str, Dict[str, Any]] = {}
        self.servers: List[Dict[str, str]] = []
        self.tags: List[Dict[str, str]] = []
        
        # Initialize default components
        self._initialize_default_components()
    
    def _initialize_default_components(self):
        """Initialize default OpenAPI components"""
        # Default security schemes
        self.add_security_scheme("ApiKeyAuth", {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for authentication"
        })
        
        self.add_security_scheme("BearerAuth", {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token for authentication"
        })
        
        # Default schemas
        self.add_schema(OpenAPISchema(
            name="Error",
            schema_type=DataType.OBJECT,
            properties={
                "error": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "integer", "description": "Error code"},
                        "name": {"type": "string", "description": "Error name"},
                        "description": {"type": "string", "description": "Error description"}
                    },
                    "required": ["code", "name", "description"]
                },
                "timestamp": {"type": "string", "format": "date-time"},
                "path": {"type": "string"},
                "method": {"type": "string"}
            },
            required=["error", "timestamp"],
            description="Standard error response"
        ))
        
        self.add_schema(OpenAPISchema(
            name="PaginationMeta",
            schema_type=DataType.OBJECT,
            properties={
                "page": {"type": "integer", "minimum": 1, "description": "Current page number"},
                "per_page": {"type": "integer", "minimum": 1, "maximum": 100, "description": "Items per page"},
                "total": {"type": "integer", "minimum": 0, "description": "Total number of items"},
                "pages": {"type": "integer", "minimum": 0, "description": "Total number of pages"}
            },
            required=["page", "per_page", "total", "pages"],
            description="Pagination metadata"
        ))
        
        # Default tags
        self.add_tag("System", "System management and health checks")
        self.add_tag("Trading", "Trading operations and order management")
        self.add_tag("Portfolio", "Portfolio management and positions")
        self.add_tag("Market Data", "Market data and quotes")
        self.add_tag("Risk", "Risk management and monitoring")
        self.add_tag("Analytics", "Analytics and reporting")
    
    def add_server(self, url: str, description: str = ""):
        """Add server to specification"""
        self.servers.append({"url": url, "description": description})
    
    def add_tag(self, name: str, description: str = ""):
        """Add tag to specification"""
        self.tags.append({"name": name, "description": description})
    
    def add_security_scheme(self, name: str, scheme: Dict[str, Any]):
        """Add security scheme"""
        self.security_schemes[name] = scheme
    
    def add_schema(self, schema: OpenAPISchema):
        """Add schema definition"""
        self.schemas[schema.name] = schema
    
    def add_endpoint(self, endpoint: OpenAPIEndpoint):
        """Add endpoint definition"""
        self.endpoints.append(endpoint)
    
    def from_flask_restx(self, api: Api) -> 'OpenAPIGenerator':
        """Generate specification from Flask-RESTX API"""
        if not FLASK_AVAILABLE:
            raise ImportError("Flask-RESTX is required for this method")
        
        # Extract basic info
        self.title = api.title or self.title
        self.version = api.version or self.version
        self.description = api.description or self.description
        
        # Extract namespaces and resources
        for namespace in api.namespaces:
            tag_name = namespace.name.title()
            self.add_tag(tag_name, namespace.description or "")
            
            for resource_class, urls, kwargs in namespace.resources:
                for url in urls:
                    self._extract_resource_endpoints(resource_class, url, tag_name, namespace.path)
        
        return self
    
    def _extract_resource_endpoints(self, resource_class: Type[Resource], url: str, tag: str, base_path: str):
        """Extract endpoints from Flask-RESTX resource"""
        for method_name in ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']:
            if hasattr(resource_class, method_name):
                method_func = getattr(resource_class, method_name)
                
                # Extract documentation from decorators or docstring
                summary = f"{method_name.upper()} {url}"
                description = method_func.__doc__ or ""
                
                # Create endpoint
                endpoint = OpenAPIEndpoint(
                    path=base_path + url,
                    method=method_name.upper(),
                    summary=summary,
                    description=description.strip(),
                    tags=[tag],
                    operation_id=f"{method_name}_{resource_class.__name__}"
                )
                
                # Extract parameters from URL
                self._extract_url_parameters(endpoint, url)
                
                # Add common responses
                self._add_common_responses(endpoint)
                
                self.add_endpoint(endpoint)
    
    def _extract_url_parameters(self, endpoint: OpenAPIEndpoint, url: str):
        """Extract parameters from URL path"""
        import re
        
        # Find path parameters like <int:id> or <string:name>
        param_pattern = r'<(?:(\w+):)?(\w+)>'
        matches = re.findall(param_pattern, url)
        
        for param_type, param_name in matches:
            data_type = DataType.STRING
            if param_type == 'int':
                data_type = DataType.INTEGER
            elif param_type == 'float':
                data_type = DataType.NUMBER
            
            parameter = OpenAPIParameter(
                name=param_name,
                location=ParameterLocation.PATH,
                data_type=data_type,
                required=True,
                description=f"Path parameter: {param_name}"
            )
            
            endpoint.parameters.append(parameter)
    
    def _add_common_responses(self, endpoint: OpenAPIEndpoint):
        """Add common responses to endpoint"""
        # Success response (method-specific)
        if endpoint.method == 'GET':
            endpoint.responses.append(OpenAPIResponse(
                status_code=200,
                description="Successful response"
            ))
        elif endpoint.method == 'POST':
            endpoint.responses.append(OpenAPIResponse(
                status_code=201,
                description="Resource created successfully"
            ))
        elif endpoint.method in ['PUT', 'PATCH']:
            endpoint.responses.append(OpenAPIResponse(
                status_code=200,
                description="Resource updated successfully"
            ))
        elif endpoint.method == 'DELETE':
            endpoint.responses.append(OpenAPIResponse(
                status_code=204,
                description="Resource deleted successfully"
            ))
        
        # Common error responses
        endpoint.responses.extend([
            OpenAPIResponse(
                status_code=400,
                description="Bad request",
                schema={"$ref": "#/components/schemas/Error"}
            ),
            OpenAPIResponse(
                status_code=401,
                description="Unauthorized",
                schema={"$ref": "#/components/schemas/Error"}
            ),
            OpenAPIResponse(
                status_code=403,
                description="Forbidden",
                schema={"$ref": "#/components/schemas/Error"}
            ),
            OpenAPIResponse(
                status_code=404,
                description="Not found",
                schema={"$ref": "#/components/schemas/Error"}
            ),
            OpenAPIResponse(
                status_code=429,
                description="Too many requests",
                schema={"$ref": "#/components/schemas/Error"}
            ),
            OpenAPIResponse(
                status_code=500,
                description="Internal server error",
                schema={"$ref": "#/components/schemas/Error"}
            )
        ])
    
    def generate_specification(self) -> Dict[str, Any]:
        """Generate complete OpenAPI 3.0 specification"""
        spec = {
            "openapi": "3.0.3",
            "info": {
                "title": self.title,
                "description": self.description,
                "version": self.version,
                "contact": {
                    "name": "API Support",
                    "url": "https://example.com/support",
                    "email": "support@example.com"
                },
                "license": {
                    "name": "MIT",
                    "url": "https://opensource.org/licenses/MIT"
                }
            },
            "servers": self.servers or [{"url": "http://localhost:8000", "description": "Development server"}],
            "tags": self.tags,
            "paths": self._generate_paths(),
            "components": {
                "schemas": self._generate_schemas(),
                "securitySchemes": self.security_schemes,
                "parameters": self._generate_common_parameters(),
                "responses": self._generate_common_responses(),
                "examples": self._generate_examples()
            },
            "security": [
                {"ApiKeyAuth": []},
                {"BearerAuth": []}
            ]
        }
        
        return spec
    
    def _generate_paths(self) -> Dict[str, Any]:
        """Generate paths section of specification"""
        paths = {}
        
        for endpoint in self.endpoints:
            if endpoint.path not in paths:
                paths[endpoint.path] = {}
            
            operation = {
                "summary": endpoint.summary,
                "description": endpoint.description,
                "tags": endpoint.tags,
                "operationId": endpoint.operation_id,
                "parameters": [self._parameter_to_dict(param) for param in endpoint.parameters],
                "responses": {
                    str(response.status_code): self._response_to_dict(response)
                    for response in endpoint.responses
                },
                "security": endpoint.security or [{"ApiKeyAuth": []}, {"BearerAuth": []}]
            }
            
            if endpoint.request_body:
                operation["requestBody"] = endpoint.request_body
            
            if endpoint.deprecated:
                operation["deprecated"] = True
            
            paths[endpoint.path][endpoint.method.lower()] = operation
        
        return paths
    
    def _generate_schemas(self) -> Dict[str, Any]:
        """Generate schemas section of specification"""
        schemas = {}
        
        for name, schema in self.schemas.items():
            schema_dict = {
                "type": schema.schema_type.value,
                "description": schema.description
            }
            
            if schema.properties:
                schema_dict["properties"] = schema.properties
            
            if schema.required:
                schema_dict["required"] = schema.required
            
            if schema.example:
                schema_dict["example"] = schema.example
            
            if not schema.additional_properties:
                schema_dict["additionalProperties"] = False
            
            schemas[name] = schema_dict
        
        return schemas
    
    def _generate_common_parameters(self) -> Dict[str, Any]:
        """Generate common parameters"""
        return {
            "PageParam": {
                "name": "page",
                "in": "query",
                "description": "Page number for pagination",
                "required": False,
                "schema": {
                    "type": "integer",
                    "minimum": 1,
                    "default": 1
                }
            },
            "PerPageParam": {
                "name": "per_page",
                "in": "query",
                "description": "Number of items per page",
                "required": False,
                "schema": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 20
                }
            },
            "SortParam": {
                "name": "sort",
                "in": "query",
                "description": "Sort field and direction (e.g., 'name:asc', 'created_at:desc')",
                "required": False,
                "schema": {
                    "type": "string",
                    "pattern": "^[a-zA-Z_][a-zA-Z0-9_]*:(asc|desc)$"
                }
            }
        }
    
    def _generate_common_responses(self) -> Dict[str, Any]:
        """Generate common responses"""
        return {
            "BadRequest": {
                "description": "Bad request",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/Error"}
                    }
                }
            },
            "Unauthorized": {
                "description": "Unauthorized",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/Error"}
                    }
                }
            },
            "Forbidden": {
                "description": "Forbidden",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/Error"}
                    }
                }
            },
            "NotFound": {
                "description": "Resource not found",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/Error"}
                    }
                }
            },
            "TooManyRequests": {
                "description": "Too many requests",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/Error"}
                    }
                },
                "headers": {
                    "X-RateLimit-Limit": {
                        "description": "Request limit per time window",
                        "schema": {"type": "integer"}
                    },
                    "X-RateLimit-Remaining": {
                        "description": "Remaining requests in current window",
                        "schema": {"type": "integer"}
                    },
                    "X-RateLimit-Reset": {
                        "description": "Time when rate limit resets",
                        "schema": {"type": "integer"}
                    },
                    "Retry-After": {
                        "description": "Seconds to wait before retrying",
                        "schema": {"type": "integer"}
                    }
                }
            },
            "InternalServerError": {
                "description": "Internal server error",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/Error"}
                    }
                }
            }
        }
    
    def _generate_examples(self) -> Dict[str, Any]:
        """Generate common examples"""
        return {
            "ErrorExample": {
                "summary": "Example error response",
                "value": {
                    "error": {
                        "code": 400,
                        "name": "Bad Request",
                        "description": "The request was invalid"
                    },
                    "timestamp": "2024-01-15T10:30:00Z",
                    "path": "/api/v1/example",
                    "method": "POST"
                }
            },
            "PaginationExample": {
                "summary": "Example pagination metadata",
                "value": {
                    "page": 1,
                    "per_page": 20,
                    "total": 150,
                    "pages": 8
                }
            }
        }
    
    def _parameter_to_dict(self, param: OpenAPIParameter) -> Dict[str, Any]:
        """Convert parameter to dictionary"""
        param_dict = {
            "name": param.name,
            "in": param.location.value,
            "description": param.description,
            "required": param.required,
            "schema": {
                "type": param.data_type.value
            }
        }
        
        if param.format:
            param_dict["schema"]["format"] = param.format
        
        if param.default is not None:
            param_dict["schema"]["default"] = param.default
        
        if param.example is not None:
            param_dict["example"] = param.example
        
        if param.enum:
            param_dict["schema"]["enum"] = param.enum
        
        if param.minimum is not None:
            param_dict["schema"]["minimum"] = param.minimum
        
        if param.maximum is not None:
            param_dict["schema"]["maximum"] = param.maximum
        
        if param.pattern:
            param_dict["schema"]["pattern"] = param.pattern
        
        return param_dict
    
    def _response_to_dict(self, response: OpenAPIResponse) -> Dict[str, Any]:
        """Convert response to dictionary"""
        response_dict = {
            "description": response.description
        }
        
        if response.schema:
            response_dict["content"] = {
                "application/json": {
                    "schema": response.schema
                }
            }
        
        if response.examples:
            if "content" not in response_dict:
                response_dict["content"] = {"application/json": {}}
            response_dict["content"]["application/json"]["examples"] = response.examples
        
        if response.headers:
            response_dict["headers"] = response.headers
        
        return response_dict
    
    def save_specification(self, file_path: str, format: str = "json"):
        """Save specification to file"""
        spec = self.generate_specification()
        
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        if format.lower() == "json":
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(spec, f, indent=2, ensure_ascii=False)
        elif format.lower() in ["yaml", "yml"]:
            with open(path, 'w', encoding='utf-8') as f:
                yaml.dump(spec, f, default_flow_style=False, allow_unicode=True)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        self.logger.info(f"OpenAPI specification saved to {path}")
    
    def generate_html_documentation(self) -> str:
        """Generate HTML documentation with Swagger UI"""
        spec_json = json.dumps(self.generate_specification(), indent=2)
        
        html_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - API Documentation</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui.css" />
    <style>
        html {
            box-sizing: border-box;
            overflow: -moz-scrollbars-vertical;
            overflow-y: scroll;
        }
        *, *:before, *:after {
            box-sizing: inherit;
        }
        body {
            margin:0;
            background: #fafafa;
        }
        .swagger-ui .topbar {
            background-color: #2c3e50;
        }
        .swagger-ui .topbar .download-url-wrapper .select-label {
            color: #ffffff;
        }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {
            const ui = SwaggerUIBundle({
                spec: {{ spec_json | safe }},
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout",
                validatorUrl: null,
                tryItOutEnabled: true,
                supportedSubmitMethods: ['get', 'post', 'put', 'delete', 'patch'],
                onComplete: function() {
                    console.log("Swagger UI loaded successfully");
                },
                onFailure: function(data) {
                    console.error("Failed to load Swagger UI", data);
                }
            });
        };
    </script>
</body>
</html>
        '''
        
        if FLASK_AVAILABLE:
            return render_template_string(html_template, 
                                        title=self.title, 
                                        spec_json=spec_json)
        else:
            return html_template.replace('{{ title }}', self.title).replace('{{ spec_json | safe }}', spec_json)

def create_openapi_generator(title: str = "API", version: str = "1.0.0", description: str = "") -> OpenAPIGenerator:
    """Create OpenAPI generator instance"""
    return OpenAPIGenerator(title=title, version=version, description=description)

# Example usage and testing
if __name__ == "__main__":
    # Create generator
    generator = create_openapi_generator(
        title="Nautilus Trader API",
        version="3.0.0",
        description="Advanced REST API for algorithmic trading platform"
    )
    
    # Add servers
    generator.add_server("https://api.nautilustrader.io/v1", "Production server")
    generator.add_server("https://staging-api.nautilustrader.io/v1", "Staging server")
    generator.add_server("http://localhost:8000/api/v1", "Development server")
    
    # Add custom schema
    generator.add_schema(OpenAPISchema(
        name="Order",
        schema_type=DataType.OBJECT,
        properties={
            "order_id": {"type": "string", "description": "Unique order identifier"},
            "symbol": {"type": "string", "description": "Trading symbol"},
            "side": {"type": "string", "enum": ["buy", "sell"], "description": "Order side"},
            "quantity": {"type": "number", "minimum": 0, "description": "Order quantity"},
            "price": {"type": "number", "minimum": 0, "description": "Order price"},
            "order_type": {"type": "string", "enum": ["market", "limit", "stop"], "description": "Order type"},
            "status": {"type": "string", "enum": ["pending", "filled", "cancelled"], "description": "Order status"},
            "created_at": {"type": "string", "format": "date-time", "description": "Creation timestamp"}
        },
        required=["order_id", "symbol", "side", "quantity", "order_type", "status"],
        description="Trading order",
        example={
            "order_id": "ord_123456",
            "symbol": "AAPL",
            "side": "buy",
            "quantity": 100,
            "price": 150.25,
            "order_type": "limit",
            "status": "pending",
            "created_at": "2024-01-15T10:30:00Z"
        }
    ))
    
    # Add custom endpoint
    generator.add_endpoint(OpenAPIEndpoint(
        path="/trading/orders",
        method="POST",
        summary="Create new order",
        description="Create a new trading order",
        tags=["Trading"],
        request_body={
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Order"}
                }
            }
        },
        responses=[
            OpenAPIResponse(
                status_code=201,
                description="Order created successfully",
                schema={"$ref": "#/components/schemas/Order"}
            )
        ]
    ))
    
    # Generate and save specification
    spec = generator.generate_specification()
    print("Generated OpenAPI specification with:")
    print(f"- {len(spec['paths'])} endpoints")
    print(f"- {len(spec['components']['schemas'])} schemas")
    print(f"- {len(spec['components']['securitySchemes'])} security schemes")
    
    # Save to files
    generator.save_specification("openapi.json", "json")
    generator.save_specification("openapi.yaml", "yaml")
    
    # Generate HTML documentation
    html_doc = generator.generate_html_documentation()
    with open("api_docs.html", "w", encoding="utf-8") as f:
        f.write(html_doc)
    
    print("Documentation files generated successfully!")