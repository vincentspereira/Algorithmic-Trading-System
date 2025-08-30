#!/usr/bin/env python3
"""
Database Setup and Migration Script
Automated database initialization and schema management

Usage:
    python setup_database.py [--init] [--migrate] [--seed] [--reset]
"""

import asyncio
import argparse
import logging
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.database_manager import (
    DatabaseManager, DatabaseConfig, create_database_config,
    User, TradingAccount, Order, Position, Strategy
)
from sqlalchemy.ext.asyncio import create_async_engine
import uuid
from datetime import datetime, timedelta
import bcrypt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseSetup:
    """Database setup and migration manager"""
    
    def __init__(self):
        self.config = create_database_config()
        self.db_manager = None
    
    async def initialize_manager(self):
        """Initialize database manager"""
        self.db_manager = DatabaseManager(self.config)
        await self.db_manager.initialize()
    
    async def create_databases(self):
        """Create databases if they don't exist"""
        logger.info("Creating databases...")
        
        # Create PostgreSQL database
        await self._create_postgres_database()
        
        # Create ClickHouse database
        await self._create_clickhouse_database()
        
        logger.info("Databases created successfully")
    
    async def _create_postgres_database(self):
        """Create PostgreSQL database"""
        try:
            # Connect to default postgres database to create our database
            admin_connection_string = (
                f"postgresql+asyncpg://{self.config.postgres_user}:"
                f"{self.config.postgres_password}@{self.config.postgres_host}:"
                f"{self.config.postgres_port}/postgres"
            )
            
            admin_engine = create_async_engine(admin_connection_string)
            
            async with admin_engine.begin() as conn:
                # Check if database exists
                result = await conn.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (self.config.postgres_database,)
                )
                
                if not result.fetchone():
                    # Create database
                    await conn.execute(f"CREATE DATABASE {self.config.postgres_database}")
                    logger.info(f"Created PostgreSQL database: {self.config.postgres_database}")
                else:
                    logger.info(f"PostgreSQL database already exists: {self.config.postgres_database}")
            
            await admin_engine.dispose()
            
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL database: {e}")
    
    async def _create_clickhouse_database(self):
        """Create ClickHouse database"""
        try:
            if not self.db_manager.clickhouse_client:
                logger.warning("ClickHouse not available, skipping database creation")
                return
            
            # Create database
            self.db_manager.clickhouse_client.execute(
                f"CREATE DATABASE IF NOT EXISTS {self.config.clickhouse_database}"
            )
            
            logger.info(f"Created ClickHouse database: {self.config.clickhouse_database}")
            
        except Exception as e:
            logger.error(f"Failed to create ClickHouse database: {e}")
    
    async def create_tables(self):
        """Create all database tables"""
        logger.info("Creating database tables...")
        
        # Create PostgreSQL tables
        await self.db_manager.create_tables()
        
        # Create ClickHouse tables
        await self.db_manager.create_clickhouse_tables()
        
        logger.info("Database tables created successfully")
    
    async def seed_data(self):
        """Seed database with initial data"""
        logger.info("Seeding database with initial data...")
        
        async with self.db_manager.get_postgres_session() as session:
            # Create demo user
            demo_user = User(
                username="demo_user",
                email="demo@trading.com",
                password_hash=bcrypt.hashpw("demo123".encode(), bcrypt.gensalt()).decode(),
                is_active=True,
                is_verified=True,
                permissions=["read", "write", "trade"]
            )
            session.add(demo_user)
            await session.flush()
            
            # Create demo trading account
            demo_account = TradingAccount(
                user_id=demo_user.id,
                account_name="Demo Paper Trading",
                broker="IBKR",
                account_number="DUK221396",
                account_type="PAPER",
                api_credentials={"encrypted": True},
                is_active=True
            )
            session.add(demo_account)
            await session.flush()
            
            # Create sample strategy
            sample_strategy = Strategy(
                user_id=demo_user.id,
                name="RSI Mean Reversion",
                description="Simple RSI-based mean reversion strategy",
                strategy_type="mean_reversion",
                parameters={
                    "rsi_period": 14,
                    "rsi_oversold": 30,
                    "rsi_overbought": 70,
                    "symbols": ["AAPL", "MSFT", "GOOGL"]
                },
                is_active=False
            )
            session.add(sample_strategy)
            
            await session.commit()
            
            logger.info("Database seeded with demo data")
    
    async def reset_database(self):
        """Reset database (drop and recreate)"""
        logger.warning("Resetting database - all data will be lost!")
        
        try:
            # Drop PostgreSQL tables
            if self.db_manager.postgres_engine:
                async with self.db_manager.postgres_engine.begin() as conn:
                    await conn.run_sync(lambda sync_conn: 
                        self.db_manager.postgres_engine.sync_engine.metadata.drop_all(sync_conn))
            
            # Drop ClickHouse tables
            if self.db_manager.clickhouse_client:
                tables = ["market_data", "tick_data", "indicator_data"]
                for table in tables:
                    try:
                        self.db_manager.clickhouse_client.execute(f"DROP TABLE IF EXISTS {table}")
                    except Exception as e:
                        logger.warning(f"Failed to drop ClickHouse table {table}: {e}")
            
            # Clear Redis
            if self.db_manager.redis_pool:
                async with self.db_manager.get_redis_client() as redis:
                    await redis.flushdb()
            
            logger.info("Database reset completed")
            
        except Exception as e:
            logger.error(f"Failed to reset database: {e}")
    
    async def check_health(self):
        """Check database health"""
        logger.info("Checking database health...")
        
        health_status = self.db_manager.get_health_status()
        
        for db_name, status in health_status.items():
            status_text = "✅ HEALTHY" if status else "❌ UNHEALTHY"
            logger.info(f"{db_name.upper()}: {status_text}")
        
        overall_health = all(health_status.values())
        logger.info(f"Overall Database Health: {'✅ HEALTHY' if overall_health else '❌ ISSUES DETECTED'}")
        
        return overall_health
    
    async def run_migrations(self):
        """Run database migrations"""
        logger.info("Running database migrations...")
        
        # For now, we'll just ensure tables exist
        # In a production system, you'd have versioned migration files
        await self.create_tables()
        
        logger.info("Database migrations completed")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.db_manager:
            await self.db_manager.cleanup()

async def main():
    """Main setup function"""
    parser = argparse.ArgumentParser(description="Database Setup and Migration")
    parser.add_argument("--init", action="store_true", help="Initialize databases and tables")
    parser.add_argument("--migrate", action="store_true", help="Run database migrations")
    parser.add_argument("--seed", action="store_true", help="Seed database with initial data")
    parser.add_argument("--reset", action="store_true", help="Reset database (WARNING: destroys all data)")
    parser.add_argument("--health", action="store_true", help="Check database health")
    parser.add_argument("--all", action="store_true", help="Run full setup (init + migrate + seed)")
    
    args = parser.parse_args()
    
    if not any([args.init, args.migrate, args.seed, args.reset, args.health, args.all]):
        parser.print_help()
        return
    
    setup = DatabaseSetup()
    
    try:
        await setup.initialize_manager()
        
        if args.reset:
            await setup.reset_database()
        
        if args.init or args.all:
            await setup.create_databases()
            await setup.create_tables()
        
        if args.migrate or args.all:
            await setup.run_migrations()
        
        if args.seed or args.all:
            await setup.seed_data()
        
        if args.health or args.all:
            healthy = await setup.check_health()
            if not healthy:
                sys.exit(1)
        
        print("\n🎉 Database setup completed successfully!")
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        sys.exit(1)
    
    finally:
        await setup.cleanup()

if __name__ == "__main__":
    asyncio.run(main())