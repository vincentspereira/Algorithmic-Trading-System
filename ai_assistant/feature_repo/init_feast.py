"""
Initialize Feast Feature Store for AI Assistant

This script initializes the Feast feature store, applies feature definitions,
and sets up the repository for the AI Assistant.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

try:
    from feast import FeatureStore
    from features import (
        ticker_entity,
        daily_market_features,
        technical_indicators,
        market_sentiment,
        ai_trading_decision_service,
        ai_risk_assessment_service,
        ai_market_analysis_service
    )
    FEAST_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Feast not available or feature definitions not found: {e}")
    print("Please install Feast with: pip install feast")
    FEAST_AVAILABLE = False


def check_prerequisites():
    """Check if all prerequisites are met"""
    print("Checking prerequisites...")
    
    # Check if feature_store.yaml exists
    config_file = current_dir / "feature_store.yaml"
    if not config_file.exists():
        print(f"✗ feature_store.yaml not found at {config_file}")
        return False
    else:
        print(f"✓ feature_store.yaml found")
    
    # Check if sample data exists
    data_file = current_dir / "data" / "market_data.parquet"
    if not data_file.exists():
        print(f"✗ Sample data not found at {data_file}")
        print("  Run generate_sample_data.py first to create sample data")
        return False
    else:
        print(f"✓ Sample data found")
    
    # Check if Feast is available
    if not FEAST_AVAILABLE:
        print("✗ Feast is not available")
        return False
    else:
        print("✓ Feast is available")
    
    return True


def initialize_feature_store():
    """Initialize the Feast feature store"""
    print("\nInitializing Feast Feature Store...")
    print("=" * 50)
    
    try:
        # Initialize feature store
        store = FeatureStore(repo_path=str(current_dir))
        print("✓ Feature store initialized")
        
        # Apply entity
        print("Applying entity definitions...")
        store.apply([ticker_entity])
        print("✓ Entity applied: ticker")
        
        # Apply feature views
        print("Applying feature view definitions...")
        feature_views = [
            daily_market_features,
            technical_indicators,
            market_sentiment
        ]
        
        for fv in feature_views:
            store.apply([fv])
            print(f"✓ Feature view applied: {fv.name}")
        
        # Apply feature services
        print("Applying feature service definitions...")
        feature_services = [
            ai_trading_decision_service,
            ai_risk_assessment_service,
            ai_market_analysis_service
        ]
        
        for fs in feature_services:
            store.apply([fs])
            print(f"✓ Feature service applied: {fs.name}")
        
        print("\n✓ All feature definitions applied successfully!")
        return store
        
    except Exception as e:
        print(f"✗ Error initializing feature store: {e}")
        return None


def materialize_features(store):
    """Materialize features to online store"""
    print("\nMaterializing features to online store...")
    print("=" * 50)
    
    try:
        from datetime import datetime, timedelta
        
        # Materialize features for the last 7 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        print(f"Materializing features from {start_date} to {end_date}")
        
        # Get all feature views
        feature_views = [
            "daily_market_features",
            "technical_indicators", 
            "market_sentiment"
        ]
        
        store.materialize(
            start_date=start_date,
            end_date=end_date,
            feature_views=feature_views
        )
        
        print("✓ Features materialized successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Error materializing features: {e}")
        print("Note: This is expected if Redis is not running")
        return False


def test_feature_retrieval(store):
    """Test feature retrieval from the store"""
    print("\nTesting feature retrieval...")
    print("=" * 50)
    
    try:
        # Test online features
        entity_rows = [
            {"ticker": "AAPL"},
            {"ticker": "GOOGL"},
            {"ticker": "MSFT"}
        ]
        
        features = [
            "daily_market_features:closing_price",
            "daily_market_features:daily_volume",
            "technical_indicators:rsi_14",
            "market_sentiment:sentiment_score"
        ]
        
        print("Testing online feature retrieval...")
        online_features = store.get_online_features(
            features=features,
            entity_rows=entity_rows
        )
        
        print("✓ Online features retrieved successfully!")
        print("Sample features:")
        df = online_features.to_df()
        print(df.head())
        
        return True
        
    except Exception as e:
        print(f"✗ Error retrieving features: {e}")
        print("Note: This is expected if features are not materialized")
        return False


def validate_setup():
    """Validate the complete setup"""
    print("\nValidating Feast setup...")
    print("=" * 50)
    
    try:
        store = FeatureStore(repo_path=str(current_dir))
        
        # List entities
        entities = store.list_entities()
        print(f"✓ Entities: {[e.name for e in entities]}")
        
        # List feature views
        feature_views = store.list_feature_views()
        print(f"✓ Feature Views: {[fv.name for fv in feature_views]}")
        
        # List feature services
        feature_services = store.list_feature_services()
        print(f"✓ Feature Services: {[fs.name for fs in feature_services]}")
        
        print("\n✓ Feast setup validation completed!")
        return True
        
    except Exception as e:
        print(f"✗ Error validating setup: {e}")
        return False


def main():
    """Main initialization function"""
    print("AI Assistant Feast Feature Store Initialization")
    print("=" * 60)
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n✗ Prerequisites not met. Please fix the issues above.")
        sys.exit(1)
    
    # Initialize feature store
    store = initialize_feature_store()
    if not store:
        print("\n✗ Failed to initialize feature store.")
        sys.exit(1)
    
    # Materialize features (optional, may fail if Redis not running)
    materialize_features(store)
    
    # Test feature retrieval (optional, may fail if not materialized)
    test_feature_retrieval(store)
    
    # Validate setup
    if validate_setup():
        print("\n🎉 Feast Feature Store initialization completed successfully!")
        print("\nNext steps:")
        print("1. Start the Docker services: docker-compose up -d")
        print("2. The Feast feature server will be available at http://localhost:6566")
        print("3. Use the AI Assistant to query features for enhanced decision making")
    else:
        print("\n⚠️  Setup completed with warnings. Check the logs above.")


if __name__ == "__main__":
    main()