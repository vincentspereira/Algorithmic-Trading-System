"""
Feast Feature Store Setup Script

This script initializes the Feast repository, registers feature views,
sets up offline and online stores, and provides data ingestion examples
for the Nautilus Trading System.

Features:
- Initialize Feast repository
- Register all feature definitions
- Set up offline and online stores
- Data ingestion examples
- Feature materialization
- Validation and testing

Author: Kilo Code
Version: 1.0.0
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import argparse

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feature_store_config import FeatureStoreConfig, FeatureStoreManager
from feature_definitions import get_all_feature_definitions, get_feature_list_by_category

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Feast imports
try:
    from feast import FeatureStore
    FEAST_AVAILABLE = True
except ImportError:
    logger.warning("Feast not available. Install with: pip install feast")
    FEAST_AVAILABLE = False


class FeastSetupManager:
    """Manager for setting up and configuring Feast feature store"""
    
    def __init__(self, repo_path: str = "feature_repo", config: Optional[FeatureStoreConfig] = None):
        self.repo_path = Path(repo_path)
        self.config = config or FeatureStoreConfig.from_env()
        self.manager = FeatureStoreManager(self.config, str(self.repo_path))
        self.feature_definitions = None
        
    def setup_complete_feature_store(self) -> bool:
        """Complete setup of the feature store"""
        logger.info("Starting complete Feast feature store setup...")
        
        try:
            # Step 1: Initialize repository
            if not self.initialize_repository():
                return False
            
            # Step 2: Create sample data
            if not self.create_sample_data():
                return False
            
            # Step 3: Apply feature definitions
            if not self.apply_feature_definitions():
                return False
            
            # Step 4: Materialize features (optional)
            if not self.materialize_features():
                logger.warning("Feature materialization failed, but continuing...")
            
            # Step 5: Validate setup
            if not self.validate_setup():
                return False
            
            logger.info("✓ Complete Feast feature store setup completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"✗ Error in complete setup: {e}")
            return False
    
    def initialize_repository(self) -> bool:
        """Initialize the Feast repository"""
        logger.info("Initializing Feast repository...")
        
        try:
            # Initialize repository structure
            if not self.manager.initialize_repo():
                return False
            
            # Create additional directories
            data_dir = self.repo_path / "data"
            data_dir.mkdir(exist_ok=True)
            
            # Create subdirectories for different data types
            (data_dir / "market_data").mkdir(exist_ok=True)
            (data_dir / "indicators").mkdir(exist_ok=True)
            (data_dir / "signals").mkdir(exist_ok=True)
            (data_dir / "volume_profiles").mkdir(exist_ok=True)
            
            logger.info("✓ Repository initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"✗ Error initializing repository: {e}")
            return False
    
    def create_sample_data(self) -> bool:
        """Create sample data files for testing"""
        logger.info("Creating sample data files...")
        
        try:
            data_dir = self.repo_path / "data"
            
            # Generate sample market data
            market_data = self._generate_sample_market_data()
            market_data.to_parquet(data_dir / "market_data.parquet", index=False)
            logger.info(f"✓ Created market data with {len(market_data)} records")
            
            # Generate sample technical indicators
            indicators_data = self._generate_sample_indicators(market_data)
            indicators_data.to_parquet(data_dir / "technical_indicators.parquet", index=False)
            logger.info(f"✓ Created indicators data with {len(indicators_data)} records")
            
            # Generate sample trading signals
            signals_data = self._generate_sample_signals(market_data)
            signals_data.to_parquet(data_dir / "trading_signals.parquet", index=False)
            logger.info(f"✓ Created signals data with {len(signals_data)} records")
            
            # Generate sample volume profiles
            volume_profiles = self._generate_sample_volume_profiles(market_data)
            volume_profiles.to_parquet(data_dir / "volume_profiles.parquet", index=False)
            logger.info(f"✓ Created volume profiles with {len(volume_profiles)} records")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Error creating sample data: {e}")
            return False
    
    def _generate_sample_market_data(self, days: int = 30) -> pd.DataFrame:
        """Generate sample OHLCV market data"""
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
        
        data = []
        base_date = datetime.now() - timedelta(days=days)
        
        for symbol in symbols:
            # Generate price series
            np.random.seed(hash(symbol) % 2**32)  # Consistent seed per symbol
            base_price = np.random.uniform(100, 500)
            
            for day in range(days):
                for hour in range(24):  # Hourly data
                    timestamp = base_date + timedelta(days=day, hours=hour)
                    
                    # Generate OHLCV data
                    price_change = np.random.normal(0, 0.02)  # 2% volatility
                    open_price = base_price * (1 + price_change)
                    high_price = open_price * (1 + abs(np.random.normal(0, 0.01)))
                    low_price = open_price * (1 - abs(np.random.normal(0, 0.01)))
                    close_price = np.random.uniform(low_price, high_price)
                    volume = int(np.random.lognormal(10, 1))
                    
                    # Calculate derived fields
                    typical_price = (high_price + low_price + close_price) / 3
                    vwap = typical_price  # Simplified
                    price_change_val = close_price - open_price
                    price_change_pct = price_change_val / open_price * 100
                    
                    data.append({
                        "symbol": symbol,
                        "timestamp": timestamp,
                        "created_timestamp": timestamp,
                        "open_price": round(open_price, 2),
                        "high_price": round(high_price, 2),
                        "low_price": round(low_price, 2),
                        "close_price": round(close_price, 2),
                        "volume": volume,
                        "vwap": round(vwap, 2),
                        "typical_price": round(typical_price, 2),
                        "price_change": round(price_change_val, 2),
                        "price_change_pct": round(price_change_pct, 2),
                        "volume_change": np.random.normal(0, 0.1),
                        "volume_change_pct": np.random.normal(0, 10),
                        "price_volatility_1h": abs(np.random.normal(0, 0.02)),
                        "price_volatility_1d": abs(np.random.normal(0, 0.05)),
                        "price_range_1h": high_price - low_price,
                        "price_range_1d": high_price - low_price,
                        "avg_spread": np.random.uniform(0.01, 0.05),
                        "bid_ask_spread": np.random.uniform(0.01, 0.03),
                        "tick_count_1h": np.random.randint(100, 1000),
                        "tick_count_1d": np.random.randint(1000, 10000),
                    })
                    
                    base_price = close_price  # Update base price
        
        return pd.DataFrame(data)
    
    def _generate_sample_indicators(self, market_data: pd.DataFrame) -> pd.DataFrame:
        """Generate sample technical indicators data"""
        indicators_data = []
        
        for symbol in market_data['symbol'].unique():
            symbol_data = market_data[market_data['symbol'] == symbol].sort_values('timestamp')
            
            for _, row in symbol_data.iterrows():
                close_price = row['close_price']
                
                # Generate sample indicators (simplified calculations)
                indicators_data.append({
                    "symbol": symbol,
                    "timestamp": row['timestamp'],
                    "created_timestamp": row['created_timestamp'],
                    # Moving averages
                    "sma_5": close_price * np.random.uniform(0.98, 1.02),
                    "sma_10": close_price * np.random.uniform(0.97, 1.03),
                    "sma_20": close_price * np.random.uniform(0.95, 1.05),
                    "sma_50": close_price * np.random.uniform(0.90, 1.10),
                    "sma_200": close_price * np.random.uniform(0.80, 1.20),
                    "ema_5": close_price * np.random.uniform(0.98, 1.02),
                    "ema_10": close_price * np.random.uniform(0.97, 1.03),
                    "ema_20": close_price * np.random.uniform(0.95, 1.05),
                    "ema_50": close_price * np.random.uniform(0.90, 1.10),
                    "ema_200": close_price * np.random.uniform(0.80, 1.20),
                    "vw_sma_20": close_price * np.random.uniform(0.95, 1.05),
                    "vw_ema_20": close_price * np.random.uniform(0.95, 1.05),
                    # Momentum indicators
                    "rsi_14": np.random.uniform(20, 80),
                    "rsi_21": np.random.uniform(25, 75),
                    "stoch_k": np.random.uniform(20, 80),
                    "stoch_d": np.random.uniform(20, 80),
                    "williams_r": np.random.uniform(-80, -20),
                    "roc_10": np.random.uniform(-5, 5),
                    "momentum_10": np.random.uniform(-2, 2),
                    # Trend indicators
                    "macd_line": np.random.uniform(-2, 2),
                    "macd_signal": np.random.uniform(-2, 2),
                    "macd_histogram": np.random.uniform(-1, 1),
                    "vw_macd_line": np.random.uniform(-2, 2),
                    "vw_macd_signal": np.random.uniform(-2, 2),
                    "vw_macd_histogram": np.random.uniform(-1, 1),
                    "adx": np.random.uniform(10, 50),
                    "plus_di": np.random.uniform(10, 40),
                    "minus_di": np.random.uniform(10, 40),
                    "aroon_up": np.random.uniform(0, 100),
                    "aroon_down": np.random.uniform(0, 100),
                    # Volatility indicators
                    "bb_upper": close_price * 1.02,
                    "bb_middle": close_price,
                    "bb_lower": close_price * 0.98,
                    "bb_width": close_price * 0.04,
                    "bb_percent": np.random.uniform(0, 1),
                    "atr_14": close_price * np.random.uniform(0.01, 0.05),
                    "atr_21": close_price * np.random.uniform(0.01, 0.05),
                    "keltner_upper": close_price * 1.015,
                    "keltner_lower": close_price * 0.985,
                    "donchian_upper": close_price * 1.03,
                    "donchian_lower": close_price * 0.97,
                })
        
        return pd.DataFrame(indicators_data)
    
    def _generate_sample_signals(self, market_data: pd.DataFrame) -> pd.DataFrame:
        """Generate sample trading signals data"""
        signals_data = []
        
        for symbol in market_data['symbol'].unique():
            symbol_data = market_data[market_data['symbol'] == symbol].sort_values('timestamp')
            
            # Generate signals every few hours
            for i in range(0, len(symbol_data), 6):  # Every 6 hours
                row = symbol_data.iloc[i]
                close_price = row['close_price']
                
                signal_direction = np.random.choice(["BUY", "SELL", "HOLD"], p=[0.3, 0.3, 0.4])
                
                signals_data.append({
                    "symbol": symbol,
                    "timestamp": row['timestamp'],
                    "created_timestamp": row['created_timestamp'],
                    "signal_strength": np.random.uniform(0.1, 1.0),
                    "signal_direction": signal_direction,
                    "signal_confidence": np.random.uniform(0.5, 0.95),
                    "entry_price": close_price,
                    "stop_loss": close_price * (0.95 if signal_direction == "BUY" else 1.05),
                    "take_profit": close_price * (1.05 if signal_direction == "BUY" else 0.95),
                    "risk_reward_ratio": np.random.uniform(1.5, 3.0),
                    "signal_source": np.random.choice(["MA_CROSSOVER", "RSI_DIVERGENCE", "MACD_SIGNAL"]),
                    "signal_timestamp": int(row['timestamp'].timestamp()),
                    "signal_expiry": int((row['timestamp'] + timedelta(hours=4)).timestamp()),
                    # Strategy performance
                    "strategy_win_rate": np.random.uniform(0.45, 0.65),
                    "strategy_avg_return": np.random.uniform(-0.02, 0.05),
                    "strategy_sharpe_ratio": np.random.uniform(0.5, 2.0),
                    "strategy_max_drawdown": np.random.uniform(0.05, 0.20),
                    "strategy_total_trades": np.random.randint(50, 500),
                    "strategy_profitable_trades": np.random.randint(25, 300),
                    "strategy_last_signal_time": int(row['timestamp'].timestamp()),
                    "strategy_active": np.random.choice([True, False], p=[0.8, 0.2]),
                })
        
        return pd.DataFrame(signals_data)
    
    def _generate_sample_volume_profiles(self, market_data: pd.DataFrame) -> pd.DataFrame:
        """Generate sample volume profile data"""
        volume_profiles = []
        
        for symbol in market_data['symbol'].unique():
            symbol_data = market_data[market_data['symbol'] == symbol].sort_values('timestamp')
            
            # Generate volume profiles every 4 hours
            for i in range(0, len(symbol_data), 4):
                row = symbol_data.iloc[i]
                close_price = row['close_price']
                
                volume_profiles.append({
                    "symbol": symbol,
                    "timestamp": row['timestamp'],
                    "created_timestamp": row['created_timestamp'],
                    "poc_price": close_price * np.random.uniform(0.99, 1.01),  # Point of Control
                    "vah_price": close_price * np.random.uniform(1.01, 1.03),  # Value Area High
                    "val_price": close_price * np.random.uniform(0.97, 0.99),  # Value Area Low
                    "volume_at_price_current": int(row['volume'] * np.random.uniform(0.1, 0.3)),
                    "volume_imbalance": np.random.uniform(-0.5, 0.5),
                    "volume_delta": int(np.random.normal(0, 1000)),
                    "cumulative_volume_delta": int(np.random.normal(0, 5000)),
                    "volume_weighted_price": close_price * np.random.uniform(0.995, 1.005),
                    "volume_profile_shape": np.random.choice(["normal", "bimodal", "flat"], p=[0.6, 0.3, 0.1]),
                    "high_volume_nodes": f"[{close_price:.2f}, {close_price*1.01:.2f}]",
                    "low_volume_nodes": f"[{close_price*0.99:.2f}, {close_price*1.02:.2f}]",
                })
        
        return pd.DataFrame(volume_profiles)
    
    def apply_feature_definitions(self) -> bool:
        """Apply all feature definitions to the store"""
        logger.info("Applying feature definitions...")
        
        if not FEAST_AVAILABLE:
            logger.warning("Feast not available, skipping feature definition application")
            return True
        
        try:
            # Get all feature definitions
            self.feature_definitions = get_all_feature_definitions()
            
            # Prepare all objects for application
            objects_to_apply = []
            objects_to_apply.extend(self.feature_definitions["entities"])
            objects_to_apply.extend(self.feature_definitions["feature_views"])
            objects_to_apply.extend(self.feature_definitions["on_demand_features"])
            objects_to_apply.extend(self.feature_definitions["feature_services"])
            
            # Apply to store
            if objects_to_apply:
                success = self.manager.apply_features(objects_to_apply)
                if success:
                    logger.info(f"✓ Applied {len(objects_to_apply)} feature definitions")
                    return True
                else:
                    logger.error("✗ Failed to apply feature definitions")
                    return False
            else:
                logger.warning("No feature definitions to apply")
                return True
                
        except Exception as e:
            logger.error(f"✗ Error applying feature definitions: {e}")
            return False
    
    def materialize_features(self) -> bool:
        """Materialize features to online store"""
        logger.info("Materializing features to online store...")
        
        if not FEAST_AVAILABLE:
            logger.warning("Feast not available, skipping materialization")
            return True
        
        try:
            # Materialize incremental features
            end_date = datetime.now()
            success = self.manager.materialize_incremental(end_date)
            
            if success:
                logger.info("✓ Feature materialization completed")
                return True
            else:
                logger.warning("Feature materialization failed")
                return False
                
        except Exception as e:
            logger.error(f"Error in feature materialization: {e}")
            return False
    
    def validate_setup(self) -> bool:
        """Validate the feature store setup"""
        logger.info("Validating feature store setup...")
        
        try:
            # Check if repository exists
            if not self.repo_path.exists():
                logger.error("Repository path does not exist")
                return False
            
            # Check if config file exists
            config_file = self.repo_path / "feature_store.yaml"
            if not config_file.exists():
                logger.error("feature_store.yaml not found")
                return False
            
            # Check if data files exist
            data_dir = self.repo_path / "data"
            required_files = [
                "market_data.parquet",
                "technical_indicators.parquet", 
                "trading_signals.parquet",
                "volume_profiles.parquet"
            ]
            
            for file_name in required_files:
                file_path = data_dir / file_name
                if not file_path.exists():
                    logger.error(f"Required data file not found: {file_name}")
                    return False
            
            # Test feature store connection if Feast is available
            if FEAST_AVAILABLE:
                store = self.manager.get_feature_store()
                if store is None:
                    logger.error("Could not connect to feature store")
                    return False
                
                # Test getting feature services
                try:
                    feature_services = store.list_feature_services()
                    logger.info(f"Found {len(feature_services)} feature services")
                except Exception as e:
                    logger.warning(f"Could not list feature services: {e}")
            
            logger.info("✓ Feature store validation completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"✗ Error in validation: {e}")
            return False
    
    def demonstrate_feature_retrieval(self) -> bool:
        """Demonstrate feature retrieval from the store"""
        logger.info("Demonstrating feature retrieval...")
        
        if not FEAST_AVAILABLE:
            logger.warning("Feast not available, skipping demonstration")
            return True
        
        try:
            store = self.manager.get_feature_store()
            if not store:
                logger.error("Could not get feature store")
                return False
            
            # Example: Get online features
            entity_rows = [
                {"symbol": "AAPL"},
                {"symbol": "GOOGL"},
            ]
            
            features = [
                "ohlcv_features:close_price",
                "ohlcv_features:volume",
                "moving_averages:sma_20",
                "momentum_indicators:rsi_14",
            ]
            
            try:
                online_features = self.manager.get_online_features(features, entity_rows)
                if online_features:
                    logger.info("✓ Successfully retrieved online features")
                    logger.info(f"Features shape: {len(online_features)} features")
                else:
                    logger.warning("No online features retrieved")
            except Exception as e:
                logger.warning(f"Could not retrieve online features: {e}")
            
            # Example: Get feature service
            try:
                trading_service = self.manager.get_feature_service("trading_decision_v1")
                if trading_service:
                    logger.info("✓ Successfully retrieved trading decision service")
                else:
                    logger.warning("Could not retrieve trading decision service")
            except Exception as e:
                logger.warning(f"Could not retrieve feature service: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error in feature retrieval demonstration: {e}")
            return False
    
    def print_setup_summary(self):
        """Print summary of the setup"""
        logger.info("Feature Store Setup Summary")
        logger.info("=" * 50)
        logger.info(f"Repository Path: {self.repo_path}")
        logger.info(f"Project Name: {self.config.project_name}")
        logger.info(f"Offline Store: {self.config.offline_store_type}")
        logger.info(f"Online Store: {self.config.online_store_type}")
        
        if self.feature_definitions:
            logger.info(f"Entities: {len(self.feature_definitions['entities'])}")
            logger.info(f"Feature Views: {len(self.feature_definitions['feature_views'])}")
            logger.info(f"Feature Services: {len(self.feature_definitions['feature_services'])}")
        
        # Print feature categories
        feature_categories = get_feature_list_by_category()
        logger.info("Feature Categories:")
        for category, features in feature_categories.items():
            logger.info(f"  {category}: {len(features)} features")


def main():
    """Main function to run the setup"""
    parser = argparse.ArgumentParser(description='Setup Feast Feature Store for Nautilus Trading')
    parser.add_argument('--repo-path', default='feature_repo', help='Path to feature repository')
    parser.add_argument('--skip-materialization', action='store_true', help='Skip feature materialization')
    parser.add_argument('--demo', action='store_true', help='Run feature retrieval demonstration')
    
    args = parser.parse_args()
    
    # Create setup manager
    setup_manager = FeastSetupManager(repo_path=args.repo_path)
    
    # Run complete setup
    success = setup_manager.setup_complete_feature_store()
    
    if success:
        logger.info("✓ Feast feature store setup completed successfully!")
        
        # Run demonstration if requested
        if args.demo:
            setup_manager.demonstrate_feature_retrieval()
        
        # Print summary
        setup_manager.print_setup_summary()
        
        return 0
    else:
        logger.error("✗ Feast feature store setup failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())