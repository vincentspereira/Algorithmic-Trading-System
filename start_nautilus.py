#!/usr/bin/env python3
"""
NautilusTrader Engine Startup Script

Convenient startup script for the NautilusTrader engine with Interactive Brokers integration.
This script provides easy commands to start the engine in different modes and configurations.

Usage Examples:
    python start_nautilus.py                    # Start in paper trading mode
    python start_nautilus.py --live             # Start in live trading mode
    python start_nautilus.py --test             # Run integration tests
    python start_nautilus.py --test --full      # Run full test suite
    python start_nautilus.py --status           # Check system status
    python start_nautilus.py --validate         # Validate configuration

Author: Vincent S. Pereira
Version: 1.0.0
Phase: 1 - Core System Validation & Hardening
"""

import asyncio
import argparse
import sys
import os
import subprocess
from pathlib import Path
import logging
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_dependencies() -> bool:
    """
    Check if required dependencies are available.
    """
    logger.info("Checking dependencies...")
    
    required_packages = [
        'nautilus_trader',
        'fastapi',
        'uvicorn',
        'pydantic',
        'asyncio'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            logger.debug(f"✓ {package} available")
        except ImportError:
            missing_packages.append(package)
            logger.warning(f"✗ {package} not available")
    
    if missing_packages:
        logger.error(f"Missing required packages: {', '.join(missing_packages)}")
        logger.info("Install missing packages with: pip install nautilus_trader fastapi uvicorn")
        return False
    
    logger.info("All dependencies available")
    return True


def validate_configuration() -> bool:
    """
    Validate system configuration.
    """
    logger.info("Validating configuration...")
    
    try:
        from shared.config import settings
        
        # Check required settings
        required_settings = [
            'IB_HOST',
            'IB_PAPER_PORT',
            'IB_LIVE_PORT',
            'IB_PAPER_CLIENT_ID',
            'IB_LIVE_CLIENT_ID'
        ]
        
        missing_settings = []
        for setting in required_settings:
            if not hasattr(settings, setting):
                missing_settings.append(setting)
        
        if missing_settings:
            logger.error(f"Missing configuration settings: {', '.join(missing_settings)}")
            return False
        
        # Validate configuration files exist
        config_files = [
            'shared/config.py',
            'nautilus_trader_engine/config/ib_config.py'
        ]
        
        for config_file in config_files:
            if not Path(config_file).exists():
                logger.error(f"Configuration file not found: {config_file}")
                return False
        
        logger.info("Configuration validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        return False


def check_system_status() -> dict:
    """
    Check overall system status.
    """
    logger.info("Checking system status...")
    
    status = {
        'dependencies': check_dependencies(),
        'configuration': validate_configuration(),
        'engine_files': True,
        'services': True
    }
    
    # Check critical files exist
    critical_files = [
        'nautilus_trader_engine/main.py',
        'nautilus_trader_engine/services/trading_gateway.py',
        'nautilus_trader_engine/services/risk_management_service.py',
        'nautilus_trader_engine/config/ib_config.py'
    ]
    
    for file_path in critical_files:
        if not Path(file_path).exists():
            logger.error(f"Critical file missing: {file_path}")
            status['engine_files'] = False
    
    # Overall status
    status['overall'] = all(status.values())
    
    return status


async def start_engine(mode: str = "paper", **kwargs) -> None:
    """
    Start the NautilusTrader engine.
    """
    logger.info(f"Starting NautilusTrader engine in {mode} mode...")
    
    try:
        from nautilus_trader_engine.main import main as engine_main
        
        # Set command line arguments for the engine
        original_argv = sys.argv.copy()
        sys.argv = ['main.py', '--mode', mode]
        
        if kwargs.get('log_level'):
            sys.argv.extend(['--log-level', kwargs['log_level']])
        
        if kwargs.get('config'):
            sys.argv.extend(['--config', kwargs['config']])
        
        # Start the engine
        await engine_main()
        
    except KeyboardInterrupt:
        logger.info("Engine stopped by user")
    except Exception as e:
        logger.error(f"Engine error: {e}")
        raise
    finally:
        # Restore original argv
        sys.argv = original_argv


async def run_tests(mode: str = "paper", full: bool = False) -> None:
    """
    Run integration tests.
    """
    logger.info(f"Running integration tests for {mode} mode...")
    
    try:
        from nautilus_trader_engine.test_integration import main as test_main
        
        # Set command line arguments for tests
        original_argv = sys.argv.copy()
        sys.argv = ['test_integration.py', '--mode', mode, '--save-results']
        
        if full:
            sys.argv.append('--full')
        
        # Run tests
        await test_main()
        
    except Exception as e:
        logger.error(f"Test error: {e}")
        raise
    finally:
        # Restore original argv
        sys.argv = original_argv


def print_status_report(status: dict) -> None:
    """
    Print a formatted status report.
    """
    print("\n" + "="*60)
    print("NAUTILUS TRADER SYSTEM STATUS")
    print("="*60)
    
    status_symbol = "✓" if status['overall'] else "✗"
    overall_status = "READY" if status['overall'] else "NOT READY"
    print(f"Overall Status: {status_symbol} {overall_status}")
    
    print("\nComponent Status:")
    for component, is_ok in status.items():
        if component != 'overall':
            symbol = "✓" if is_ok else "✗"
            component_name = component.replace('_', ' ').title()
            print(f"  {symbol} {component_name}")
    
    if not status['overall']:
        print("\nPlease resolve the issues above before starting the engine.")
    else:
        print("\nSystem is ready to start!")
        print("\nQuick Start Commands:")
        print("  python start_nautilus.py              # Start paper trading")
        print("  python start_nautilus.py --live       # Start live trading")
        print("  python start_nautilus.py --test       # Run tests")
    
    print("="*60)


def main():
    """
    Main entry point for the startup script.
    """
    parser = argparse.ArgumentParser(
        description="NautilusTrader Engine Startup Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start_nautilus.py                    # Start in paper trading mode
  python start_nautilus.py --live             # Start in live trading mode
  python start_nautilus.py --test             # Run integration tests
  python start_nautilus.py --test --full      # Run full test suite
  python start_nautilus.py --status           # Check system status
  python start_nautilus.py --validate         # Validate configuration only
        """
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--paper",
        action="store_const",
        const="paper",
        dest="mode",
        help="Start in paper trading mode (default)"
    )
    mode_group.add_argument(
        "--live",
        action="store_const",
        const="live",
        dest="mode",
        help="Start in live trading mode"
    )
    
    # Action selection
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument(
        "--test",
        action="store_true",
        help="Run integration tests instead of starting engine"
    )
    action_group.add_argument(
        "--status",
        action="store_true",
        help="Check system status and exit"
    )
    action_group.add_argument(
        "--validate",
        action="store_true",
        help="Validate configuration and exit"
    )
    
    # Additional options
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full test suite (both paper and live modes)"
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
    
    # Set default mode
    if not args.mode:
        args.mode = "paper"
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    try:
        if args.status:
            # Check and display system status
            status = check_system_status()
            print_status_report(status)
            sys.exit(0 if status['overall'] else 1)
        
        elif args.validate:
            # Validate configuration only
            if validate_configuration():
                logger.info("Configuration validation passed")
                sys.exit(0)
            else:
                logger.error("Configuration validation failed")
                sys.exit(1)
        
        elif args.test:
            # Run tests
            asyncio.run(run_tests(mode=args.mode, full=args.full))
        
        else:
            # Check system status before starting
            status = check_system_status()
            if not status['overall']:
                logger.error("System not ready. Use --status to see details.")
                sys.exit(1)
            
            # Start the engine
            asyncio.run(start_engine(
                mode=args.mode,
                config=args.config,
                log_level=args.log_level
            ))
    
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
    except Exception as e:
        logger.error(f"Startup script error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()