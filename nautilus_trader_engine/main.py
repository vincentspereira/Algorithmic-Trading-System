#!/usr/bin/env python3
"""
NautilusTrader Engine Main Service

This is the main entry point for the NautilusTrader engine service that integrates
with Interactive Brokers for both paper and live trading.

Features:
- Interactive Brokers integration for paper and live trading
- Real-time market data feeds with fallback mechanisms
- Risk management and position monitoring
- Order management and execution
- WebSocket API for real-time updates
- Comprehensive logging and monitoring

Usage:
    python main.py --mode paper    # Start in paper trading mode
    python main.py --mode live     # Start in live trading mode
    python main.py --config custom_config.json  # Use custom configuration

Author: Vincent S. Pereira
Version: 1.0.0
Phase: 1 - Core System Validation & Hardening
"""

import asyncio
import argparse
import logging
import signal
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import configuration and services
from shared.config import settings
from nautilus_trader_engine.config.ib_config import (
    get_ib_trading_node_config,
    get_ib_paper_trading_config,
    get_ib_live_trading_config
)
from nautilus_trader_engine.services.trading_gateway import TradingGateway
from nautilus_trader_engine.services.risk_management_service import RiskManagementService

# Try to import NautilusTrader components with fallbacks
try:
    from nautilus_trader.live.node import TradingNode
    from nautilus_trader.config import TradingNodeConfig
    from nautilus_trader.model.identifiers import TraderId
    NAUTILUS_AVAILABLE = True
except ImportError:
    NAUTILUS_AVAILABLE = False
    print("Warning: NautilusTrader not available. Running in simulation mode.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nautilus_trader_engine.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class NautilusTraderEngine:
    """
    Main NautilusTrader Engine service that orchestrates trading operations.
    
    This service manages:
    - Trading node lifecycle
    - Interactive Brokers connection
    - Risk management
    - Market data feeds
    - Order execution
    """
    
    def __init__(self, mode: str = "paper", config_path: Optional[str] = None):
        self.mode = mode.lower()
        self.config_path = config_path
        self.trading_node: Optional[Any] = None
        self.trading_gateway: Optional[TradingGateway] = None
        self.risk_service: Optional[RiskManagementService] = None
        self.is_running = False
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Validate mode
        if self.mode not in ["paper", "live"]:
            raise ValueError(f"Invalid mode '{mode}'. Must be 'paper' or 'live'.")
        
        logger.info(f"Initializing NautilusTrader Engine in {self.mode} mode")
    
    async def initialize(self) -> None:
        """
        Initialize all engine components.
        """
        try:
            logger.info("Starting engine initialization...")
            
            # Get event loop
            self.loop = asyncio.get_event_loop()
            
            # Initialize risk management service
            self.risk_service = RiskManagementService()
            await self.risk_service.initialize()
            logger.info("Risk management service initialized")
            
            # Get trading configuration
            if NAUTILUS_AVAILABLE:
                config = get_ib_trading_node_config(self.mode)
                logger.info(f"Loaded {self.mode} trading configuration")
                
                # Initialize trading node
                self.trading_node = TradingNode(config=config)
                logger.info("NautilusTrader node initialized")
            else:
                logger.warning("NautilusTrader not available - using simulation mode")
            
            # Initialize trading gateway
            gateway_config = self._get_gateway_config()
            self.trading_gateway = TradingGateway(
                loop=self.loop,
                risk_management_service=self.risk_service,
                config=gateway_config
            )
            
            logger.info("Engine initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize engine: {e}")
            raise
    
    def _get_gateway_config(self) -> Dict[str, Any]:
        """
        Get configuration for the trading gateway based on mode.
        """
        if self.mode == "paper":
            return {
                "host": settings.IB_HOST,
                "port": settings.IB_PAPER_PORT,
                "client_id": settings.IB_PAPER_CLIENT_ID,
                "account": settings.IB_PAPER_ACCOUNT,
                "mode": "paper"
            }
        else:
            return {
                "host": settings.IB_HOST,
                "port": settings.IB_LIVE_PORT,
                "client_id": settings.IB_LIVE_CLIENT_ID,
                "account": settings.IB_LIVE_ACCOUNT,
                "mode": "live"
            }
    
    async def start(self) -> None:
        """
        Start the trading engine.
        """
        try:
            logger.info(f"Starting NautilusTrader Engine in {self.mode} mode...")
            
            # Start trading node if available
            if self.trading_node and NAUTILUS_AVAILABLE:
                # Register Interactive Brokers factory classes before building
                try:
                    from nautilus_trader.adapters.interactive_brokers.factories import InteractiveBrokersLiveDataClientFactory
                    from nautilus_trader.adapters.interactive_brokers.factories import InteractiveBrokersLiveExecClientFactory
                    
                    self.trading_node.add_data_client_factory("IB", InteractiveBrokersLiveDataClientFactory)
                    self.trading_node.add_exec_client_factory("IB", InteractiveBrokersLiveExecClientFactory)
                    logger.info("Interactive Brokers factory classes registered successfully")
                except ImportError as e:
                    logger.warning(f"Could not register IB factories: {e}")
                
                # Note: TradingNode uses run_async() method, not start()
                # For now, we'll just build the node and mark it as ready
                self.trading_node.build()
                logger.info("NautilusTrader node built and ready")
            
            # Connect trading gateway
            if self.trading_gateway:
                await self.trading_gateway.connect()
                logger.info("Trading gateway connected")
            
            self.is_running = True
            logger.info(f"NautilusTrader Engine started successfully in {self.mode} mode")
            
            # Log connection status
            await self._log_connection_status()
            
        except Exception as e:
            logger.error(f"Failed to start engine: {e}")
            await self.stop()
            raise
    
    async def stop(self) -> None:
        """
        Stop the trading engine gracefully.
        """
        logger.info("Stopping NautilusTrader Engine...")
        
        self.is_running = False
        
        try:
            # Disconnect trading gateway
            if self.trading_gateway:
                await self.trading_gateway.disconnect()
                logger.info("Trading gateway disconnected")
            
            # Stop trading node
            if self.trading_node and NAUTILUS_AVAILABLE:
                try:
                    # Note: TradingNode uses dispose() method for cleanup
                    self.trading_node.dispose()
                    logger.info("NautilusTrader node disposed")
                except Exception as dispose_error:
                    logger.warning(f"Error during node disposal: {dispose_error}")
            
            # Stop risk service
            if self.risk_service:
                await self.risk_service.shutdown()
                logger.info("Risk management service stopped")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        
        logger.info("NautilusTrader Engine stopped")
    
    async def _log_connection_status(self) -> None:
        """
        Log the current connection status and configuration.
        """
        status = {
            "timestamp": datetime.now().isoformat(),
            "mode": self.mode,
            "nautilus_available": NAUTILUS_AVAILABLE,
            "trading_node_active": self.trading_node is not None,
            "trading_gateway_active": self.trading_gateway is not None,
            "risk_service_active": self.risk_service is not None,
        }
        
        if self.mode == "paper":
            status.update({
                "ib_host": settings.IB_HOST,
                "ib_port": settings.IB_PAPER_PORT,
                "ib_account": settings.IB_PAPER_ACCOUNT
            })
        else:
            status.update({
                "ib_host": settings.IB_HOST,
                "ib_port": settings.IB_LIVE_PORT,
                "ib_account": settings.IB_LIVE_ACCOUNT
            })
        
        logger.info(f"Engine Status: {status}")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check of all engine components.
        """
        health = {
            "status": "healthy" if self.is_running else "stopped",
            "timestamp": datetime.now().isoformat(),
            "mode": self.mode,
            "components": {
                "trading_node": "active" if self.trading_node else "inactive",
                "trading_gateway": "active" if self.trading_gateway else "inactive",
                "risk_service": "active" if self.risk_service else "inactive"
            }
        }
        
        # Check individual component health
        if self.risk_service:
            try:
                risk_health = await self.risk_service.health_check()
                health["components"]["risk_service_details"] = risk_health
            except Exception as e:
                health["components"]["risk_service_error"] = str(e)
        
        return health


def setup_signal_handlers(engine: NautilusTraderEngine) -> None:
    """
    Setup signal handlers for graceful shutdown.
    """
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        asyncio.create_task(engine.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main() -> None:
    """
    Main entry point for the NautilusTrader Engine.
    """
    parser = argparse.ArgumentParser(description="NautilusTrader Engine Service")
    parser.add_argument(
        "--mode",
        choices=["paper", "live"],
        default="paper",
        help="Trading mode: paper or live (default: paper)"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to custom configuration file"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Initialize engine
    engine = NautilusTraderEngine(mode=args.mode, config_path=args.config)
    
    # Setup signal handlers
    setup_signal_handlers(engine)
    
    try:
        # Initialize and start engine
        await engine.initialize()
        await engine.start()
        
        # Keep running until stopped
        logger.info("Engine is running. Press Ctrl+C to stop.")
        while engine.is_running:
            await asyncio.sleep(1)
            
            # Periodic health check
            if datetime.now().second % 60 == 0:  # Every minute
                health = await engine.health_check()
                logger.debug(f"Health check: {health['status']}")
    
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Engine error: {e}")
    finally:
        await engine.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)