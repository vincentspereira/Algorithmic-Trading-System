#!/usr/bin/env python3
"""
API Server Startup Script
Comprehensive Trading System API

Usage:
    python run_api.py [--host HOST] [--port PORT] [--workers WORKERS]
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def setup_logging():
    """Configure logging for the API server"""
    # Create logs directory
    os.makedirs("api/logs", exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("api/logs/api.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    """Main entry point for the API server"""
    parser = argparse.ArgumentParser(description="Algorithmic Trading System API")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    print("🚀 Starting Algorithmic Trading System API")
    print(f"📡 Server: http://{args.host}:{args.port}")
    print(f"📚 Documentation: http://{args.host}:{args.port}/api/docs")
    print(f"🔍 Redoc: http://{args.host}:{args.port}/api/redoc")
    print(f"📊 Metrics: http://{args.host}:{args.port}/metrics")
    print(f"💓 Health: http://{args.host}:{args.port}/health")
    
    # Run the server
    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        workers=args.workers if not args.reload else 1,
        reload=args.reload,
        log_level="debug" if args.debug else "info",
        access_log=True
    )

if __name__ == "__main__":
    main()