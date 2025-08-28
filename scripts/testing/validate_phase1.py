#!/usr/bin/env python3
"""
Phase 1 Infrastructure Validation Script
Algorithmic Trading System

This script validates that all Phase 1 services are running correctly
and can communicate with each other.
"""

import asyncio
import aiohttp
import psycopg2
import time
import sys
import json
from typing import Dict, List, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Phase1Validator:
    def __init__(self):
        self.services = {
            'nautilus_trader_engine': 'http://localhost:8000',
            'prometheus': 'http://localhost:9090',
            'grafana': 'http://localhost:3000',
            'schema_registry': 'http://localhost:8081',
            'pgadmin': 'http://localhost:5433',
            'clickhouse': 'http://localhost:8123',
            'jmx_exporter': 'http://localhost:5556'
        }
        
        self.database_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'trading_system',
            'user': 'trading_admin',
            'password': 'secure_trading_password_2024'  # Update this to match your .env
        }
        
        self.results = {}

    async def validate_http_service(self, service_name: str, url: str, expected_status: int = 200) -> Tuple[bool, str]:
        """Validate that an HTTP service is responding"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == expected_status:
                        return True, f"✅ {service_name} is healthy (HTTP {response.status})"
                    else:
                        return False, f"❌ {service_name} returned HTTP {response.status}"
        except asyncio.TimeoutError:
            return False, f"❌ {service_name} timed out"
        except Exception as e:
            return False, f"❌ {service_name} error: {str(e)}"

    async def validate_nautilus_trader_engine(self) -> Tuple[bool, str]:
        """Validate Nautilus Trader Engine specific endpoints"""
        try:
            async with aiohttp.ClientSession() as session:
                # Test health endpoint
                async with session.get(f"{self.services['nautilus_trader_engine']}/health") as response:
                    if response.status != 200:
                        return False, f"❌ Health endpoint failed: HTTP {response.status}"
                    
                    health_data = await response.json()
                    if health_data.get('status') != 'healthy':
                        return False, f"❌ Service reports unhealthy: {health_data}"

                # Test status endpoint
                async with session.get(f"{self.services['nautilus_trader_engine']}/status") as response:
                    if response.status != 200:
                        return False, f"❌ Status endpoint failed: HTTP {response.status}"
                    
                    status_data = await response.json()
                    services = status_data.get('services', {})
                    
                    # Check service connections
                    required_connections = ['kafka_connected', 'postgres_connected', 'clickhouse_connected', 'duckdb_connected']
                    for conn in required_connections:
                        if not services.get(conn, False):
                            return False, f"❌ {conn} is not established"

                return True, "✅ Nautilus Trader Engine is fully operational"
                
        except Exception as e:
            return False, f"❌ Nautilus Trader Engine validation failed: {str(e)}"

    def validate_postgresql(self) -> Tuple[bool, str]:
        """Validate PostgreSQL connection and pgvector extension"""
        try:
            conn = psycopg2.connect(**self.database_config)
            cursor = conn.cursor()
            
            # Test basic connection
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            
            # Test pgvector extension
            cursor.execute("SELECT extname FROM pg_extension WHERE extname = 'vector';")
            vector_ext = cursor.fetchone()
            if not vector_ext:
                return False, "❌ pgvector extension not installed"
            
            # Test schemas
            cursor.execute("""
                SELECT schema_name FROM information_schema.schemata 
                WHERE schema_name IN ('trading', 'market_data', 'ai_embeddings', 'risk_management', 'audit')
            """)
            schemas = [row[0] for row in cursor.fetchall()]
            expected_schemas = ['trading', 'market_data', 'ai_embeddings', 'risk_management', 'audit']
            
            missing_schemas = set(expected_schemas) - set(schemas)
            if missing_schemas:
                return False, f"❌ Missing schemas: {missing_schemas}"
            
            # Test sample data
            cursor.execute("SELECT COUNT(*) FROM market_data.instruments;")
            instrument_count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            return True, f"✅ PostgreSQL with pgvector is operational ({instrument_count} instruments loaded)"
            
        except Exception as e:
            return False, f"❌ PostgreSQL validation failed: {str(e)}"

    async def validate_prometheus_targets(self) -> Tuple[bool, str]:
        """Validate Prometheus is scraping configured targets"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.services['prometheus']}/api/v1/targets") as response:
                    if response.status != 200:
                        return False, f"❌ Prometheus targets API failed: HTTP {response.status}"
                    
                    data = await response.json()
                    targets = data.get('data', {}).get('activeTargets', [])
                    
                    # Check for key targets
                    target_jobs = {target.get('labels', {}).get('job') for target in targets}
                    expected_jobs = {'prometheus', 'nautilus-trader-engine', 'kafka-jmx'}
                    
                    missing_jobs = expected_jobs - target_jobs
                    if missing_jobs:
                        return False, f"❌ Missing Prometheus targets: {missing_jobs}"
                    
                    # Check target health
                    unhealthy_targets = [
                        target.get('labels', {}).get('job') 
                        for target in targets 
                        if target.get('health') != 'up'
                    ]
                    
                    if unhealthy_targets:
                        return False, f"❌ Unhealthy Prometheus targets: {unhealthy_targets}"
                    
                    return True, f"✅ Prometheus monitoring {len(targets)} healthy targets"
                    
        except Exception as e:
            return False, f"❌ Prometheus validation failed: {str(e)}"

    async def run_validation(self) -> Dict[str, Tuple[bool, str]]:
        """Run all validation tests"""
        logger.info("Starting Phase 1 infrastructure validation...")
        
        # HTTP service validations
        for service_name, url in self.services.items():
            if service_name == 'nautilus_trader_engine':
                continue  # Handle separately
            
            success, message = await self.validate_http_service(service_name, url)
            self.results[service_name] = (success, message)
            logger.info(message)
            
            # Small delay between requests
            await asyncio.sleep(0.5)
        
        # Specialized validations
        logger.info("Running specialized service validations...")
        
        # Nautilus Trader Engine
        success, message = await self.validate_nautilus_trader_engine()
        self.results['nautilus_trader_detailed'] = (success, message)
        logger.info(message)
        
        # PostgreSQL
        success, message = self.validate_postgresql()
        self.results['postgresql_detailed'] = (success, message)
        logger.info(message)
        
        # Prometheus targets
        success, message = await self.validate_prometheus_targets()
        self.results['prometheus_targets'] = (success, message)
        logger.info(message)
        
        return self.results

    def print_summary(self):
        """Print validation summary"""
        print("\n" + "="*60)
        print("PHASE 1 INFRASTRUCTURE VALIDATION SUMMARY")
        print("="*60)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for success, _ in self.results.values() if success)
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\nDETAILED RESULTS:")
        print("-" * 60)
        
        for test_name, (success, message) in self.results.items():
            print(f"{test_name:25} | {message}")
        
        print("\n" + "="*60)
        
        if failed_tests == 0:
            print("🎉 ALL TESTS PASSED! Phase 1 infrastructure is ready.")
            print("\nNext steps:")
            print("1. Review the services at their respective URLs")
            print("2. Check Grafana dashboards at http://localhost:3000")
            print("3. Proceed to Phase 2 development")
            return True
        else:
            print("⚠️  SOME TESTS FAILED. Please review the failed services.")
            print("\nTroubleshooting:")
            print("1. Check docker-compose logs: docker-compose logs -f")
            print("2. Verify .env configuration")
            print("3. Ensure all services have started: docker-compose ps")
            return False

async def main():
    """Main validation function"""
    validator = Phase1Validator()
    
    print("Phase 1 Infrastructure Validation")
    print("Algorithmic Trading System")
    print("=" * 50)
    print("Waiting 10 seconds for services to stabilize...")
    await asyncio.sleep(10)
    
    try:
        await validator.run_validation()
        success = validator.print_summary()
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n❌ Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())