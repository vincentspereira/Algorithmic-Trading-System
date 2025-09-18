"""Risk Manager Service

Main service module that orchestrates all risk management components
and provides the primary interface for the risk management system.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_client import start_http_server, Counter, Histogram, Gauge

from .config.risk_config import get_config, RiskManagerConfig
from .engine.risk_engine import RiskEngine
from .api.risk_api import router as risk_router
from .models.risk_models import RiskAssessmentRequest, RiskAssessmentResponse

# Metrics
REQUEST_COUNT = Counter('risk_manager_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('risk_manager_request_duration_seconds', 'Request duration')
ACTIVE_ASSESSMENTS = Gauge('risk_manager_active_assessments', 'Active risk assessments')
RISK_VIOLATIONS = Counter('risk_manager_violations_total', 'Risk violations', ['violation_type'])

class RiskManagerService:
    """Main risk manager service class"""
    
    def __init__(self, config: Optional[RiskManagerConfig] = None):
        """Initialize risk manager service
        
        Args:
            config: Configuration object, uses default if None
        """
        self.config = config or get_config()
        self.risk_engine: Optional[RiskEngine] = None
        self.app: Optional[FastAPI] = None
        self.logger = logging.getLogger(__name__)
        self._shutdown_event = asyncio.Event()
        
        # Setup logging
        self._setup_logging()
        
        self.logger.info(f"Risk Manager Service initialized - Version {self.config.service_version}")
    
    def _setup_logging(self) -> None:
        """Setup logging configuration"""
        
        # Configure root logger
        logging.basicConfig(
            level=self.config.logging.level.value,
            format=self.config.logging.format,
            handlers=[]
        )
        
        # Console handler
        if self.config.logging.console_enabled:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.config.logging.level.value)
            formatter = logging.Formatter(self.config.logging.format)
            console_handler.setFormatter(formatter)
            logging.getLogger().addHandler(console_handler)
        
        # File handler
        if self.config.logging.file_enabled:
            from logging.handlers import RotatingFileHandler
            import os
            
            # Create logs directory if it doesn't exist
            log_dir = os.path.dirname(self.config.logging.file_path)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            
            file_handler = RotatingFileHandler(
                self.config.logging.file_path,
                maxBytes=self.config.logging.file_max_size,
                backupCount=self.config.logging.file_backup_count
            )
            file_handler.setLevel(self.config.logging.level.value)
            formatter = logging.Formatter(self.config.logging.format)
            file_handler.setFormatter(formatter)
            logging.getLogger().addHandler(file_handler)
        
        # Set module-specific log levels
        for module, level in self.config.logging.module_levels.items():
            logging.getLogger(module).setLevel(level)
    
    async def initialize(self) -> None:
        """Initialize all service components"""
        
        self.logger.info("Initializing Risk Manager Service...")
        
        try:
            # Initialize risk engine
            self.risk_engine = RiskEngine(self.config)
            await self.risk_engine.initialize()
            
            # Create FastAPI app
            self.app = self._create_app()
            
            # Start Prometheus metrics server if enabled
            if hasattr(self.config, 'metrics_port'):
                start_http_server(self.config.metrics_port)
                self.logger.info(f"Metrics server started on port {self.config.metrics_port}")
            
            self.logger.info("Risk Manager Service initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Risk Manager Service: {e}")
            raise
    
    def _create_app(self) -> FastAPI:
        """Create and configure FastAPI application"""
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Application lifespan manager"""
            # Startup
            self.logger.info("Starting Risk Manager API...")
            yield
            # Shutdown
            self.logger.info("Shutting down Risk Manager API...")
            await self.shutdown()
        
        app = FastAPI(
            title="Risk Manager API",
            description="Algorithmic Trading Risk Management System",
            version=self.config.service_version,
            lifespan=lifespan
        )
        
        # Add middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.api.cors_origins,
            allow_credentials=True,
            allow_methods=self.config.api.cors_methods,
            allow_headers=self.config.api.cors_headers,
        )
        
        app.add_middleware(GZipMiddleware, minimum_size=1000)
        
        # Add request metrics middleware
        @app.middleware("http")
        async def metrics_middleware(request, call_next):
            with REQUEST_DURATION.time():
                REQUEST_COUNT.labels(
                    method=request.method,
                    endpoint=request.url.path
                ).inc()
                response = await call_next(request)
                return response
        
        # Include routers
        app.include_router(risk_router, prefix="/api/v1")
        
        # Health check endpoint
        @app.get("/health")
        async def health_check():
            """Health check endpoint"""
            if self.risk_engine and await self.risk_engine.is_healthy():
                return {"status": "healthy", "service": "risk-manager"}
            else:
                return {"status": "unhealthy", "service": "risk-manager"}
        
        # Metrics endpoint
        @app.get("/metrics")
        async def get_metrics():
            """Get service metrics"""
            if self.risk_engine:
                return await self.risk_engine.get_metrics()
            return {"error": "Risk engine not initialized"}
        
        # Dependency injection
        app.dependency_overrides = {
            # Add dependencies here if needed
        }
        
        return app
    
    async def start(self) -> None:
        """Start the risk manager service"""
        
        self.logger.info("Starting Risk Manager Service...")
        
        try:
            # Initialize components
            await self.initialize()
            
            # Setup signal handlers
            self._setup_signal_handlers()
            
            # Start the API server
            config = uvicorn.Config(
                app=self.app,
                host=self.config.api.host,
                port=self.config.api.port,
                workers=1,  # Use 1 worker for async app
                reload=self.config.api.reload,
                log_level=self.config.logging.level.value.lower(),
                access_log=True
            )
            
            server = uvicorn.Server(config)
            
            self.logger.info(
                f"Risk Manager Service started on {self.config.api.host}:{self.config.api.port}"
            )
            
            # Run server
            await server.serve()
            
        except Exception as e:
            self.logger.error(f"Failed to start Risk Manager Service: {e}")
            raise
        finally:
            await self.shutdown()
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown"""
        
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown...")
            self._shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def shutdown(self) -> None:
        """Shutdown the risk manager service"""
        
        self.logger.info("Shutting down Risk Manager Service...")
        
        try:
            if self.risk_engine:
                await self.risk_engine.shutdown()
                self.risk_engine = None
            
            self.logger.info("Risk Manager Service shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    async def assess_risk(self, request: RiskAssessmentRequest) -> RiskAssessmentResponse:
        """Assess risk for a trading request
        
        Args:
            request: Risk assessment request
            
        Returns:
            Risk assessment response
        """
        if not self.risk_engine:
            raise RuntimeError("Risk engine not initialized")
        
        ACTIVE_ASSESSMENTS.inc()
        try:
            response = await self.risk_engine.assess_order_risk(request)
            
            # Record violations
            for violation in response.violations:
                RISK_VIOLATIONS.labels(violation_type=violation.violation_type.value).inc()
            
            return response
        finally:
            ACTIVE_ASSESSMENTS.dec()
    
    async def get_portfolio_risk(self, portfolio_id: str) -> Dict[str, Any]:
        """Get portfolio risk summary
        
        Args:
            portfolio_id: Portfolio identifier
            
        Returns:
            Portfolio risk summary
        """
        if not self.risk_engine:
            raise RuntimeError("Risk engine not initialized")
        
        return await self.risk_engine.get_portfolio_risk_summary(portfolio_id)
    
    async def update_risk_limits(self, limits: Dict[str, Any]) -> bool:
        """Update risk limits
        
        Args:
            limits: New risk limits
            
        Returns:
            True if successful
        """
        if not self.risk_engine:
            raise RuntimeError("Risk engine not initialized")
        
        return await self.risk_engine.update_risk_limits(limits)
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status
        
        Returns:
            Service status information
        """
        return {
            "service": self.config.service_name,
            "version": self.config.service_version,
            "environment": self.config.environment.value,
            "risk_engine_initialized": self.risk_engine is not None,
            "api_initialized": self.app is not None,
            "config": {
                "monitoring_enabled": self.config.monitoring.enabled,
                "api_port": self.config.api.port,
                "debug": self.config.debug
            }
        }

# Global service instance
_service: Optional[RiskManagerService] = None

def get_service() -> RiskManagerService:
    """Get global service instance"""
    global _service
    if _service is None:
        _service = RiskManagerService()
    return _service

def create_service(config: Optional[RiskManagerConfig] = None) -> RiskManagerService:
    """Create a new service instance
    
    Args:
        config: Configuration object
        
    Returns:
        New service instance
    """
    return RiskManagerService(config)

async def main():
    """Main entry point for the service"""
    
    # Create and start service
    service = get_service()
    
    try:
        await service.start()
    except KeyboardInterrupt:
        print("\nReceived interrupt signal, shutting down...")
    except Exception as e:
        print(f"Service failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Run the service
    asyncio.run(main())