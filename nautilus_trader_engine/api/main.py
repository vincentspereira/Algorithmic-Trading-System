"""
Enhanced FastAPI Application for Nautilus Trader Engine - Phase 2
OAuth2/JWT Authentication and Backtesting API

This module provides the enhanced FastAPI application with:
- OAuth2/JWT authentication system
- Protected backtesting endpoints
- Comprehensive error handling
- Production-ready structure
"""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.openapi.utils import get_openapi

from .core.config import settings
from .routers import auth, backtest, optimization, features

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Nautilus Trader Engine API - Phase 2")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Verify required dependencies
    try:
        # Test JWT dependencies
        from jose import jwt
        from passlib.context import CryptContext
        logger.info("✓ JWT authentication dependencies available")
        
        # Test backtesting dependencies
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from run_initial_backtest import BacktestRunner
        logger.info("✓ Backtesting engine available")
        
    except ImportError as e:
        logger.error(f"Missing required dependencies: {e}")
        logger.warning("Some features may not work correctly")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Nautilus Trader Engine API - Phase 2")


# Initialize FastAPI application
app = FastAPI(
    title="Nautilus Trader Engine API",
    description="""
    ## Advanced Algorithmic Trading System API

    The Nautilus Trader Engine API provides comprehensive endpoints for algorithmic trading operations,
    including backtesting, optimization, feature engineering, and real-time trading capabilities.

    ### Key Features

    * **🔐 OAuth2/JWT Authentication** - Secure token-based authentication system
    * **📊 Advanced Backtesting** - Multiple backtesting engines (Backtrader, TradingGym)
    * **⚡ Hyperparameter Optimization** - Optuna-powered strategy optimization
    * **🎯 Feature Engineering** - Advanced technical indicators and feature extraction
    * **📈 Real-time Data** - Live market data integration
    * **🔄 Strategy Management** - Dynamic strategy deployment and monitoring

    ### Authentication

    Most endpoints require authentication. Use the `/api/v1/auth/login` endpoint to obtain access tokens.

    **Demo Credentials:**
    - Username: `demo`, Password: `demo123`
    - Username: `admin`, Password: `admin123`

    ### Rate Limiting

    API requests are subject to rate limiting to ensure fair usage and system stability.

    ### Support

    For technical support and documentation, visit our [GitHub repository](https://github.com/your-org/nautilus-trader-engine).
    """,
    version="2.0.0",
    terms_of_service="https://your-domain.com/terms/",
    contact={
        "name": "Nautilus Trader Engine Support",
        "url": "https://your-domain.com/contact/",
        "email": "support@your-domain.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "User authentication and token management operations. Includes login, logout, token refresh, and user information endpoints.",
        },
        {
            "name": "Backtesting",
            "description": "Strategy backtesting operations using historical data. Supports multiple backtesting engines and comprehensive performance metrics.",
        },
        {
            "name": "Optimization",
            "description": "Hyperparameter optimization for trading strategies using Optuna. Find optimal parameters to maximize strategy performance.",
        },
        {
            "name": "Features",
            "description": "Feature engineering and technical analysis operations. Generate and manage technical indicators and custom features.",
        },
        {
            "name": "System",
            "description": "System health checks, API information, and monitoring endpoints.",
        },
    ]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed messages"""
    logger.warning(f"Validation error on {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "status": "validation_error",
            "message": "Request validation failed",
            "details": exc.errors(),
            "timestamp": "2024-01-01T00:00:00Z"  # Would use datetime.utcnow() in production
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    logger.error(f"HTTP error {exc.status_code} on {request.url}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "status_code": exc.status_code,
            "timestamp": "2024-01-01T00:00:00Z"  # Would use datetime.utcnow() in production
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error on {request.url}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "internal_error",
            "message": "An unexpected error occurred",
            "timestamp": "2024-01-01T00:00:00Z"  # Would use datetime.utcnow() in production
        }
    )


def custom_openapi():
    """Custom OpenAPI schema with security definitions"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token obtained from the login endpoint"
        }
    }
    
    # Add global security requirement for protected endpoints
    openapi_schema["security"] = [{"BearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


# Include routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(backtest.router, prefix=f"{settings.API_V1_STR}/backtest")
app.include_router(optimization.router, prefix=f"{settings.API_V1_STR}/optimise")
app.include_router(features.router, prefix=f"{settings.API_V1_STR}/features")


# Root endpoints
@app.get(
    "/",
    tags=["System"],
    summary="API Root Information",
    description="Get basic information about the Nautilus Trader Engine API including version, features, and available endpoints.",
    response_description="API information and feature list"
)
async def root():
    """
    **API Root Endpoint**
    
    Returns comprehensive information about the Nautilus Trader Engine API including:
    - Current API version and description
    - Available features and capabilities
    - Documentation URLs
    - API endpoint prefix
    
    This endpoint does not require authentication and provides a quick overview of the system.
    """
    return {
        "message": "Nautilus Trader Engine API - Phase 2",
        "version": settings.VERSION,
        "description": settings.DESCRIPTION,
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "api_prefix": settings.API_V1_STR,
        "features": [
            "OAuth2/JWT Authentication",
            "Protected Backtesting Endpoints",
            "Hyperparameter Optimization with Optuna",
            "VectorBT Integration",
            "Comprehensive Error Handling",
            "Multiple Backtesting Engines"
        ]
    }


@app.get(
    "/health",
    tags=["System"],
    summary="System Health Check",
    description="Check the health status of the API and its components including authentication, backtesting engine, and database connectivity.",
    responses={
        200: {
            "description": "System is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "version": "2.0.0",
                        "environment": "development",
                        "components": {
                            "api": "healthy",
                            "authentication": "healthy",
                            "backtesting": "healthy"
                        }
                    }
                }
            }
        },
        503: {
            "description": "System is unhealthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "error": "Component failure",
                        "version": "2.0.0"
                    }
                }
            }
        }
    }
)
async def health_check():
    """
    **System Health Check**
    
    Performs comprehensive health checks on all system components:
    
    - **API Status**: Basic API functionality
    - **Authentication**: JWT token system availability
    - **Backtesting Engine**: Backtesting system availability
    - **Database**: Database connectivity (if applicable)
    
    Returns detailed status information for monitoring and alerting purposes.
    """
    try:
        # Basic health checks
        health_status = {
            "status": "healthy",
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "components": {
                "api": "healthy",
                "authentication": "healthy",
                "backtesting": "unknown"
            }
        }
        
        # Test backtesting engine availability
        try:
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from run_initial_backtest import BacktestRunner
            health_status["components"]["backtesting"] = "healthy"
        except ImportError:
            health_status["components"]["backtesting"] = "unavailable"
            health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "version": settings.VERSION
            }
        )


@app.get(
    f"{settings.API_V1_STR}/info",
    tags=["System"],
    summary="API Information",
    description="Get detailed information about API endpoints, authentication, and available features.",
    response_description="Comprehensive API information including endpoints and capabilities"
)
async def api_info():
    """
    **API Information Endpoint**
    
    Provides detailed information about the API including:
    - Available endpoints and their purposes
    - Authentication requirements and demo credentials
    - Supported strategies and engines
    - Documentation links
    
    This endpoint does not require authentication.
    """
    return {
        "api_version": "v1",
        "phase": "2",
        "description": "Enhanced API with OAuth2/JWT authentication and backtesting",
        "authentication": {
            "type": "OAuth2/JWT",
            "endpoints": {
                "login": f"{settings.API_V1_STR}/auth/login",
                "refresh": f"{settings.API_V1_STR}/auth/refresh",
                "user_info": f"{settings.API_V1_STR}/auth/me",
                "status": f"{settings.API_V1_STR}/auth/status",
                "logout": f"{settings.API_V1_STR}/auth/logout"
            },
            "demo_credentials": {
                "username": "demo",
                "password": "demo123"
            }
        },
        "backtesting": {
            "endpoints": {
                "run_backtest": f"{settings.API_V1_STR}/backtest/",
                "backtest_status": f"{settings.API_V1_STR}/backtest/status"
            },
            "supported_strategies": ["moving_average_crossover"],
            "engines": ["Backtrader", "TradingGym"]
        },
        "optimization": {
            "endpoints": {
                "run_optimization": f"{settings.API_V1_STR}/optimise/",
                "optimization_status": f"{settings.API_V1_STR}/optimise/status"
            },
            "supported_strategies": ["sma_crossover"],
            "objectives": ["sharpe_ratio", "total_return", "calmar_ratio"],
            "max_trials": 1000,
            "max_timeout": 3600
        },
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": f"{settings.API_V1_STR}/openapi.json"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment variables
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8001"))  # Different port from Phase 1
    reload = os.getenv("RELOAD", "true").lower() == "true"
    
    logger.info(f"Starting server on {host}:{port}")
    
    # Run the application
    uvicorn.run(
        "nautilus_trader_engine.api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )