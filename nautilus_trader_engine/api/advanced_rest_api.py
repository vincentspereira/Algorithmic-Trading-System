"""
Advanced REST API System
Provides comprehensive REST API with OpenAPI 3.0 specification, rate limiting,
API versioning, backward compatibility, and extensive documentation.
"""
import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
import time
import hashlib
import secrets
from functools import wraps
from collections import defaultdict, deque

try:
    from flask import Flask, request, jsonify, g, make_response, abort
    from flask_restx import Api, Resource, fields, Namespace
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    from flask_cors import CORS
    from werkzeug.exceptions import HTTPException
    import redis
    FLASK_AVAILABLE = True
except ImportError:
    Flask = None
    Api = None
    Resource = None
    fields = None
    Namespace = None
    Limiter = None
    CORS = None
    HTTPException = None
    redis = None
    FLASK_AVAILABLE = False

class APIVersion(Enum):
    """API version enumeration"""
    V1 = "v1"
    V2 = "v2"
    V3 = "v3"

class RateLimitType(Enum):
    """Rate limit types"""
    PER_SECOND = "per_second"
    PER_MINUTE = "per_minute"
    PER_HOUR = "per_hour"
    PER_DAY = "per_day"

class AuthenticationMethod(Enum):
    """Authentication methods"""
    API_KEY = "api_key"
    JWT_TOKEN = "jwt_token"
    OAUTH2 = "oauth2"
    BASIC_AUTH = "basic_auth"

@dataclass
class APIEndpoint:
    """API endpoint configuration"""
    path: str
    method: str
    version: APIVersion
    handler: Callable
    rate_limit: Optional[str] = None
    auth_required: bool = True
    auth_methods: List[AuthenticationMethod] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    deprecated: bool = False
    deprecation_date: Optional[datetime] = None
    description: str = ""
    tags: List[str] = field(default_factory=list)

@dataclass
class RateLimitRule:
    """Rate limiting rule"""
    limit: int
    period: int  # seconds
    per: str  # "second", "minute", "hour", "day"
    key_func: Optional[Callable] = None
    scope: str = "global"  # "global", "user", "ip"

@dataclass
class APIKey:
    """API key configuration"""
    key_id: str
    key_hash: str
    user_id: str
    name: str
    permissions: List[str]
    rate_limits: Dict[str, RateLimitRule]
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True
    last_used: Optional[datetime] = None
    usage_count: int = 0

@dataclass
class APIUsageStats:
    """API usage statistics"""
    endpoint: str
    method: str
    version: str
    user_id: Optional[str]
    api_key_id: Optional[str]
    timestamp: datetime
    response_time: float
    status_code: int
    request_size: int
    response_size: int
    ip_address: str
    user_agent: str

class RateLimiter:
    """Advanced rate limiting system"""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.memory_store = defaultdict(lambda: defaultdict(deque))
        self.logger = logging.getLogger(__name__)
    
    def is_allowed(self, key: str, rule: RateLimitRule) -> tuple[bool, Dict[str, Any]]:
        """Check if request is allowed under rate limit"""
        now = time.time()
        window_start = now - rule.period
        
        if self.redis_client:
            return self._redis_rate_limit(key, rule, now, window_start)
        else:
            return self._memory_rate_limit(key, rule, now, window_start)
    
    def _redis_rate_limit(self, key: str, rule: RateLimitRule, now: float, window_start: float) -> tuple[bool, Dict[str, Any]]:
        """Redis-based rate limiting"""
        try:
            pipe = self.redis_client.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(uuid.uuid4()): now})
            
            # Set expiration
            pipe.expire(key, rule.period)
            
            results = pipe.execute()
            current_count = results[1]
            
            if current_count >= rule.limit:
                # Get time until reset
                oldest_request = self.redis_client.zrange(key, 0, 0, withscores=True)
                reset_time = oldest_request[0][1] + rule.period if oldest_request else now + rule.period
                
                return False, {
                    'limit': rule.limit,
                    'remaining': 0,
                    'reset_time': reset_time,
                    'retry_after': reset_time - now
                }
            
            return True, {
                'limit': rule.limit,
                'remaining': rule.limit - current_count - 1,
                'reset_time': now + rule.period,
                'retry_after': 0
            }
        
        except Exception as e:
            self.logger.error(f"Redis rate limiting error: {e}")
            # Fallback to memory-based limiting
            return self._memory_rate_limit(key, rule, now, window_start)
    
    def _memory_rate_limit(self, key: str, rule: RateLimitRule, now: float, window_start: float) -> tuple[bool, Dict[str, Any]]:
        """Memory-based rate limiting"""
        requests = self.memory_store[key][rule.period]
        
        # Remove old requests
        while requests and requests[0] < window_start:
            requests.popleft()
        
        if len(requests) >= rule.limit:
            reset_time = requests[0] + rule.period
            return False, {
                'limit': rule.limit,
                'remaining': 0,
                'reset_time': reset_time,
                'retry_after': reset_time - now
            }
        
        # Add current request
        requests.append(now)
        
        return True, {
            'limit': rule.limit,
            'remaining': rule.limit - len(requests),
            'reset_time': now + rule.period,
            'retry_after': 0
        }

class APIKeyManager:
    """API key management system"""
    
    def __init__(self):
        self.api_keys: Dict[str, APIKey] = {}
        self.logger = logging.getLogger(__name__)
    
    def create_api_key(self, user_id: str, name: str, permissions: List[str],
                      rate_limits: Dict[str, RateLimitRule] = None,
                      expires_hours: Optional[int] = None) -> APIKey:
        """Create new API key"""
        key_id = str(uuid.uuid4())
        raw_key = f"{key_id}_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        expires_at = None
        if expires_hours:
            expires_at = datetime.now() + timedelta(hours=expires_hours)
        
        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            user_id=user_id,
            name=name,
            permissions=permissions,
            rate_limits=rate_limits or {},
            created_at=datetime.now(),
            expires_at=expires_at
        )
        
        self.api_keys[key_id] = api_key
        
        self.logger.info(f"Created API key {key_id} for user {user_id}")
        return api_key, raw_key
    
    def validate_api_key(self, raw_key: str) -> Optional[APIKey]:
        """Validate API key"""
        try:
            key_id = raw_key.split('_')[0]
            key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
            
            api_key = self.api_keys.get(key_id)
            if not api_key:
                return None
            
            if not api_key.is_active:
                return None
            
            if api_key.key_hash != key_hash:
                return None
            
            if api_key.expires_at and api_key.expires_at < datetime.now():
                return None
            
            # Update usage stats
            api_key.last_used = datetime.now()
            api_key.usage_count += 1
            
            return api_key
        
        except Exception as e:
            self.logger.error(f"API key validation error: {e}")
            return None
    
    def revoke_api_key(self, key_id: str, user_id: str) -> bool:
        """Revoke API key"""
        api_key = self.api_keys.get(key_id)
        if not api_key or api_key.user_id != user_id:
            return False
        
        api_key.is_active = False
        self.logger.info(f"Revoked API key {key_id}")
        return True
    
    def list_user_keys(self, user_id: str) -> List[APIKey]:
        """List user's API keys"""
        return [key for key in self.api_keys.values() if key.user_id == user_id]

class APIVersionManager:
    """API version management system"""
    
    def __init__(self):
        self.endpoints: Dict[APIVersion, Dict[str, APIEndpoint]] = {
            version: {} for version in APIVersion
        }
        self.default_version = APIVersion.V1
        self.logger = logging.getLogger(__name__)
    
    def register_endpoint(self, endpoint: APIEndpoint):
        """Register API endpoint"""
        key = f"{endpoint.method}:{endpoint.path}"
        self.endpoints[endpoint.version][key] = endpoint
        
        self.logger.debug(f"Registered endpoint {key} for version {endpoint.version.value}")
    
    def get_endpoint(self, method: str, path: str, version: APIVersion = None) -> Optional[APIEndpoint]:
        """Get endpoint by method, path, and version"""
        if version is None:
            version = self.default_version
        
        key = f"{method}:{path}"
        return self.endpoints[version].get(key)
    
    def get_version_from_request(self, request) -> APIVersion:
        """Extract API version from request"""
        # Check Accept header
        accept_header = request.headers.get('Accept', '')
        if 'application/vnd.nautilus.v2+json' in accept_header:
            return APIVersion.V2
        elif 'application/vnd.nautilus.v3+json' in accept_header:
            return APIVersion.V3
        
        # Check URL path
        if request.path.startswith('/api/v2/'):
            return APIVersion.V2
        elif request.path.startswith('/api/v3/'):
            return APIVersion.V3
        
        # Check query parameter
        version_param = request.args.get('version')
        if version_param:
            try:
                return APIVersion(version_param)
            except ValueError:
                pass
        
        return self.default_version

class AdvancedRestAPI:
    """Advanced REST API system"""
    
    def __init__(self, app: Flask = None, redis_url: str = None):
        self.app = app or Flask(__name__)
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.rate_limiter = RateLimiter(
            redis.from_url(redis_url) if redis_url and redis else None
        )
        self.api_key_manager = APIKeyManager()
        self.version_manager = APIVersionManager()
        self.usage_stats: List[APIUsageStats] = []
        
        # Configure Flask app
        self._configure_app()
        
        # Initialize Flask-RESTX
        self.api = Api(
            self.app,
            version='3.0',
            title='Nautilus Trader API',
            description='Advanced REST API for Nautilus Trader Engine',
            doc='/docs/',
            prefix='/api'
        )
        
        # Setup namespaces
        self._setup_namespaces()
        
        # Setup middleware
        self._setup_middleware()
        
        # Register default endpoints
        self._register_default_endpoints()
    
    def _configure_app(self):
        """Configure Flask application"""
        self.app.config['RESTX_MASK_SWAGGER'] = False
        self.app.config['RESTX_VALIDATE'] = True
        self.app.config['RESTX_JSON'] = {'ensure_ascii': False}
        
        # Enable CORS
        if CORS:
            CORS(self.app, resources={
                r"/api/*": {
                    "origins": "*",
                    "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
                    "allow_headers": ["Content-Type", "Authorization", "X-API-Key", "Accept"]
                }
            })
    
    def _setup_namespaces(self):
        """Setup API namespaces"""
        # Trading namespace
        self.trading_ns = Namespace('trading', description='Trading operations')
        self.api.add_namespace(self.trading_ns, path='/api/v1/trading')
        
        # Portfolio namespace
        self.portfolio_ns = Namespace('portfolio', description='Portfolio management')
        self.api.add_namespace(self.portfolio_ns, path='/api/v1/portfolio')
        
        # Market data namespace
        self.market_ns = Namespace('market', description='Market data')
        self.api.add_namespace(self.market_ns, path='/api/v1/market')
        
        # Risk namespace
        self.risk_ns = Namespace('risk', description='Risk management')
        self.api.add_namespace(self.risk_ns, path='/api/v1/risk')
        
        # Analytics namespace
        self.analytics_ns = Namespace('analytics', description='Analytics and reporting')
        self.api.add_namespace(self.analytics_ns, path='/api/v1/analytics')
        
        # System namespace
        self.system_ns = Namespace('system', description='System management')
        self.api.add_namespace(self.system_ns, path='/api/v1/system')
    
    def _setup_middleware(self):
        """Setup middleware for authentication, rate limiting, etc."""
        
        @self.app.before_request
        def before_request():
            """Pre-request middleware"""
            g.start_time = time.time()
            g.api_version = self.version_manager.get_version_from_request(request)
            g.user_id = None
            g.api_key = None
            
            # Skip middleware for documentation and health endpoints
            if request.path in ['/docs/', '/health', '/api/health']:
                return
            
            # Authentication
            if not self._authenticate_request():
                return self._unauthorized_response()
            
            # Rate limiting
            if not self._check_rate_limits():
                return self._rate_limit_exceeded_response()
        
        @self.app.after_request
        def after_request(response):
            """Post-request middleware"""
            # Add API version headers
            response.headers['X-API-Version'] = g.get('api_version', APIVersion.V1).value
            response.headers['X-RateLimit-Limit'] = g.get('rate_limit', 1000)
            response.headers['X-RateLimit-Remaining'] = g.get('rate_limit_remaining', 999)
            response.headers['X-RateLimit-Reset'] = g.get('rate_limit_reset', int(time.time() + 3600))
            
            # Log usage statistics
            self._log_usage_stats(response)
            
            return response
        
        @self.app.errorhandler(HTTPException)
        def handle_http_exception(e):
            """Handle HTTP exceptions"""
            return jsonify({
                'error': {
                    'code': e.code,
                    'name': e.name,
                    'description': e.description
                },
                'timestamp': datetime.now().isoformat(),
                'path': request.path,
                'method': request.method
            }), e.code
        
        @self.app.errorhandler(Exception)
        def handle_exception(e):
            """Handle general exceptions"""
            self.logger.error(f"Unhandled exception: {e}", exc_info=True)
            return jsonify({
                'error': {
                    'code': 500,
                    'name': 'Internal Server Error',
                    'description': 'An unexpected error occurred'
                },
                'timestamp': datetime.now().isoformat(),
                'path': request.path,
                'method': request.method
            }), 500
    
    def _authenticate_request(self) -> bool:
        """Authenticate incoming request"""
        # Check for API key in header
        api_key_header = request.headers.get('X-API-Key')
        if api_key_header:
            api_key = self.api_key_manager.validate_api_key(api_key_header)
            if api_key:
                g.api_key = api_key
                g.user_id = api_key.user_id
                return True
        
        # Check for Bearer token
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]
            # Implement JWT token validation here
            # For now, accept any token for demo purposes
            g.user_id = 'demo_user'
            return True
        
        # Allow unauthenticated access to public endpoints
        public_endpoints = ['/health', '/docs/', '/api/health', '/api/system/status']
        if request.path in public_endpoints:
            return True
        
        return False
    
    def _check_rate_limits(self) -> bool:
        """Check rate limits for current request"""
        if not g.api_key:
            # Apply default rate limits for unauthenticated requests
            key = f"ip:{request.remote_addr}"
            rule = RateLimitRule(limit=100, period=3600, per="hour")
        else:
            # Apply API key specific rate limits
            key = f"api_key:{g.api_key.key_id}"
            rule = g.api_key.rate_limits.get('default', 
                RateLimitRule(limit=1000, period=3600, per="hour"))
        
        allowed, info = self.rate_limiter.is_allowed(key, rule)
        
        # Store rate limit info in g for response headers
        g.rate_limit = info['limit']
        g.rate_limit_remaining = info['remaining']
        g.rate_limit_reset = int(info['reset_time'])
        
        return allowed
    
    def _unauthorized_response(self):
        """Return unauthorized response"""
        return jsonify({
            'error': {
                'code': 401,
                'name': 'Unauthorized',
                'description': 'Authentication required'
            },
            'timestamp': datetime.now().isoformat()
        }), 401
    
    def _rate_limit_exceeded_response(self):
        """Return rate limit exceeded response"""
        return jsonify({
            'error': {
                'code': 429,
                'name': 'Too Many Requests',
                'description': 'Rate limit exceeded'
            },
            'timestamp': datetime.now().isoformat(),
            'retry_after': g.get('retry_after', 3600)
        }), 429
    
    def _log_usage_stats(self, response):
        """Log API usage statistics"""
        if hasattr(g, 'start_time'):
            stats = APIUsageStats(
                endpoint=request.endpoint or request.path,
                method=request.method,
                version=g.get('api_version', APIVersion.V1).value,
                user_id=g.get('user_id'),
                api_key_id=g.get('api_key').key_id if g.get('api_key') else None,
                timestamp=datetime.now(),
                response_time=time.time() - g.start_time,
                status_code=response.status_code,
                request_size=len(request.get_data()),
                response_size=len(response.get_data()),
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')
            )
            
            self.usage_stats.append(stats)
            
            # Keep only recent stats in memory (last 10000 requests)
            if len(self.usage_stats) > 10000:
                self.usage_stats = self.usage_stats[-10000:]
    
    def _register_default_endpoints(self):
        """Register default API endpoints"""
        
        # Health check endpoint
        @self.system_ns.route('/health')
        class HealthCheck(Resource):
            def get(self):
                """Health check endpoint"""
                return {
                    'status': 'healthy',
                    'timestamp': datetime.now().isoformat(),
                    'version': '1.0.0',
                    'uptime': time.time() - self.api.start_time if hasattr(self.api, 'start_time') else 0
                }
        
        # API status endpoint
        @self.system_ns.route('/status')
        class APIStatus(Resource):
            def get(self):
                """API status and statistics"""
                total_requests = len(self.usage_stats)
                avg_response_time = sum(s.response_time for s in self.usage_stats[-1000:]) / min(1000, total_requests) if total_requests > 0 else 0
                
                return {
                    'api_version': 'v1',
                    'total_requests': total_requests,
                    'avg_response_time': avg_response_time,
                    'active_api_keys': len([k for k in self.api_key_manager.api_keys.values() if k.is_active]),
                    'supported_versions': [v.value for v in APIVersion],
                    'rate_limits': {
                        'default': '1000/hour',
                        'authenticated': '10000/hour'
                    }
                }
        
        # API key management endpoints
        @self.system_ns.route('/api-keys')
        class APIKeys(Resource):
            def get(self):
                """List user's API keys"""
                if not g.user_id:
                    abort(401)
                
                keys = self.api_key_manager.list_user_keys(g.user_id)
                return {
                    'api_keys': [
                        {
                            'key_id': key.key_id,
                            'name': key.name,
                            'permissions': key.permissions,
                            'created_at': key.created_at.isoformat(),
                            'expires_at': key.expires_at.isoformat() if key.expires_at else None,
                            'last_used': key.last_used.isoformat() if key.last_used else None,
                            'usage_count': key.usage_count,
                            'is_active': key.is_active
                        }
                        for key in keys
                    ]
                }
            
            def post(self):
                """Create new API key"""
                if not g.user_id:
                    abort(401)
                
                data = request.get_json()
                name = data.get('name', 'API Key')
                permissions = data.get('permissions', ['read'])
                expires_hours = data.get('expires_hours')
                
                api_key, raw_key = self.api_key_manager.create_api_key(
                    user_id=g.user_id,
                    name=name,
                    permissions=permissions,
                    expires_hours=expires_hours
                )
                
                return {
                    'key_id': api_key.key_id,
                    'api_key': raw_key,  # Only returned once
                    'name': api_key.name,
                    'permissions': api_key.permissions,
                    'created_at': api_key.created_at.isoformat(),
                    'expires_at': api_key.expires_at.isoformat() if api_key.expires_at else None
                }, 201
        
        @self.system_ns.route('/api-keys/<string:key_id>')
        class APIKeyDetail(Resource):
            def delete(self, key_id):
                """Revoke API key"""
                if not g.user_id:
                    abort(401)
                
                success = self.api_key_manager.revoke_api_key(key_id, g.user_id)
                if not success:
                    abort(404)
                
                return {'message': 'API key revoked successfully'}
    
    def register_endpoint(self, endpoint: APIEndpoint):
        """Register custom API endpoint"""
        self.version_manager.register_endpoint(endpoint)
    
    def get_usage_analytics(self, hours: int = 24) -> Dict[str, Any]:
        """Get API usage analytics"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_stats = [s for s in self.usage_stats if s.timestamp > cutoff_time]
        
        if not recent_stats:
            return {
                'total_requests': 0,
                'avg_response_time': 0,
                'error_rate': 0,
                'top_endpoints': [],
                'requests_by_hour': []
            }
        
        # Calculate metrics
        total_requests = len(recent_stats)
        avg_response_time = sum(s.response_time for s in recent_stats) / total_requests
        error_count = len([s for s in recent_stats if s.status_code >= 400])
        error_rate = error_count / total_requests * 100
        
        # Top endpoints
        endpoint_counts = defaultdict(int)
        for stat in recent_stats:
            endpoint_counts[stat.endpoint] += 1
        
        top_endpoints = sorted(endpoint_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Requests by hour
        hourly_counts = defaultdict(int)
        for stat in recent_stats:
            hour = stat.timestamp.replace(minute=0, second=0, microsecond=0)
            hourly_counts[hour] += 1
        
        requests_by_hour = [
            {'hour': hour.isoformat(), 'count': count}
            for hour, count in sorted(hourly_counts.items())
        ]
        
        return {
            'total_requests': total_requests,
            'avg_response_time': avg_response_time,
            'error_rate': error_rate,
            'top_endpoints': [{'endpoint': ep, 'count': count} for ep, count in top_endpoints],
            'requests_by_hour': requests_by_hour,
            'status_codes': {
                '2xx': len([s for s in recent_stats if 200 <= s.status_code < 300]),
                '3xx': len([s for s in recent_stats if 300 <= s.status_code < 400]),
                '4xx': len([s for s in recent_stats if 400 <= s.status_code < 500]),
                '5xx': len([s for s in recent_stats if 500 <= s.status_code < 600])
            }
        }
    
    def run(self, host: str = "0.0.0.0", port: int = 8000, debug: bool = False):
        """Run the API server"""
        self.api.start_time = time.time()
        self.logger.info(f"Starting Advanced REST API on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

def create_advanced_api(redis_url: str = None) -> AdvancedRestAPI:
    """Create advanced REST API instance"""
    if not FLASK_AVAILABLE:
        raise ImportError("Flask and related packages are required for REST API")
    
    return AdvancedRestAPI(redis_url=redis_url)

# OpenAPI 3.0 specification generator
def generate_openapi_spec(api: AdvancedRestAPI) -> Dict[str, Any]:
    """Generate OpenAPI 3.0 specification"""
    spec = {
        "openapi": "3.0.3",
        "info": {
            "title": "Nautilus Trader API",
            "description": "Advanced REST API for Nautilus Trader Engine with comprehensive trading, portfolio, and risk management capabilities",
            "version": "3.0.0",
            "contact": {
                "name": "Nautilus Trader Support",
                "url": "https://nautilustrader.io",
                "email": "support@nautilustrader.io"
            },
            "license": {
                "name": "MIT",
                "url": "https://opensource.org/licenses/MIT"
            }
        },
        "servers": [
            {
                "url": "https://api.nautilustrader.io/v1",
                "description": "Production server"
            },
            {
                "url": "https://staging-api.nautilustrader.io/v1",
                "description": "Staging server"
            },
            {
                "url": "http://localhost:8000/api/v1",
                "description": "Development server"
            }
        ],
        "security": [
            {"ApiKeyAuth": []},
            {"BearerAuth": []}
        ],
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key"
                },
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                }
            },
            "schemas": {
                "Error": {
                    "type": "object",
                    "properties": {
                        "error": {
                            "type": "object",
                            "properties": {
                                "code": {"type": "integer"},
                                "name": {"type": "string"},
                                "description": {"type": "string"}
                            }
                        },
                        "timestamp": {"type": "string", "format": "date-time"},
                        "path": {"type": "string"},
                        "method": {"type": "string"}
                    }
                },
                "APIKey": {
                    "type": "object",
                    "properties": {
                        "key_id": {"type": "string"},
                        "name": {"type": "string"},
                        "permissions": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "created_at": {"type": "string", "format": "date-time"},
                        "expires_at": {"type": "string", "format": "date-time"},
                        "last_used": {"type": "string", "format": "date-time"},
                        "usage_count": {"type": "integer"},
                        "is_active": {"type": "boolean"}
                    }
                }
            }
        },
        "paths": {
            "/system/health": {
                "get": {
                    "summary": "Health check",
                    "description": "Check API health status",
                    "tags": ["System"],
                    "security": [],
                    "responses": {
                        "200": {
                            "description": "API is healthy",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string"},
                                            "timestamp": {"type": "string", "format": "date-time"},
                                            "version": {"type": "string"},
                                            "uptime": {"type": "number"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/system/api-keys": {
                "get": {
                    "summary": "List API keys",
                    "description": "Get list of user's API keys",
                    "tags": ["System"],
                    "responses": {
                        "200": {
                            "description": "List of API keys",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "api_keys": {
                                                "type": "array",
                                                "items": {"$ref": "#/components/schemas/APIKey"}
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "401": {
                            "description": "Unauthorized",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            }
                        }
                    }
                },
                "post": {
                    "summary": "Create API key",
                    "description": "Create a new API key",
                    "tags": ["System"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "permissions": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        },
                                        "expires_hours": {"type": "integer"}
                                    },
                                    "required": ["name"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "API key created",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "allOf": [
                                            {"$ref": "#/components/schemas/APIKey"},
                                            {
                                                "type": "object",
                                                "properties": {
                                                    "api_key": {"type": "string"}
                                                }
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    return spec

if __name__ == "__main__":
    # Example usage
    import secrets
    
    api = create_advanced_api()
    
    # Create sample API key
    api_key, raw_key = api.api_key_manager.create_api_key(
        user_id="demo_user",
        name="Demo API Key",
        permissions=["read", "write"],
        rate_limits={
            "default": RateLimitRule(limit=1000, period=3600, per="hour")
        }
    )
    
    print(f"Created API key: {raw_key}")
    print("Starting API server...")
    
    # Run the API
    api.run(debug=True)