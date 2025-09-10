#!/usr/bin/env python3
"""
Mock Data Generator for Testing
Generates realistic mock data for testing dependency updates and system functionality
in the Algorithmic Trading System.
"""

import json
import random
import sys
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MockDataGenerator:
    def __init__(self):
        self.data_dir = 'dependency_management/testing/mock_data'
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Trading symbols for mock data
        self.symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'AMD', 'INTC']
        
        # Dependency names for mock updates
        self.dependencies = [
            'nautilus_trader', 'kafka-python', 'langchain', 'fastapi', 'redis', 
            'postgres', 'clickhouse', 'qdrant', 'pyportfolioopt', 'riskfolio-lib'
        ]
        
        # Mock CVE data
        self.cve_templates = [
            {
                'id': 'CVE-2023-{rand}',
                'package': '{dep}',
                'version': '{version}',
                'severity': 'critical',
                'cvss_score': 9.8,
                'description': 'Remote code execution vulnerability in {dep}',
                'published': '2023-10-01'
            },
            {
                'id': 'CVE-2023-{rand}',
                'package': '{dep}',
                'version': '{version}',
                'severity': 'high',
                'cvss_score': 7.5,
                'description': 'Authentication bypass vulnerability in {dep}',
                'published': '2023-09-28'
            },
            {
                'id': 'CVE-2023-{rand}',
                'package': '{dep}',
                'version': '{version}',
                'severity': 'medium',
                'cvss_score': 5.3,
                'description': 'Information disclosure vulnerability in {dep}',
                'published': '2023-09-25'
            }
        ]
    
    def generate_mock_market_data(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """Generate mock market data for a symbol."""
        # Generate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Generate base price
        base_price = random.uniform(50, 500)
        
        # Generate price series with some randomness
        prices = [base_price]
        for i in range(1, len(dates)):
            change = random.uniform(-0.05, 0.05)  # ±5% daily change
            new_price = prices[-1] * (1 + change)
            prices.append(max(new_price, 0.01))  # Ensure positive price
        
        # Generate OHLC data
        data = []
        for i, date in enumerate(dates):
            price = prices[i]
            open_price = price * random.uniform(0.99, 1.01)
            high = price * random.uniform(1.0, 1.03)
            low = price * random.uniform(0.97, 1.0)
            close = price
            volume = random.randint(1000000, 10000000)
            
            data.append({
                'timestamp': date.isoformat(),
                'symbol': symbol,
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close, 2),
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    def generate_mock_dependency_updates(self, count: int = 10) -> List[Dict[str, Any]]:
        """Generate mock dependency update data."""
        updates = []
        
        for i in range(count):
            dep = random.choice(self.dependencies)
            current_version = f"{random.randint(1, 3)}.{random.randint(0, 9)}.{random.randint(0, 9)}"
            latest_version = f"{random.randint(int(current_version.split('.')[0]), 5)}.{random.randint(0, 15)}.{random.randint(0, 15)}"
            
            # Determine severity based on version difference
            current_parts = [int(x) for x in current_version.split('.')]
            latest_parts = [int(x) for x in latest_version.split('.')]
            
            if latest_parts[0] > current_parts[0]:
                severity = 'high'  # Major version bump
            elif latest_parts[1] > current_parts[1]:
                severity = 'medium'  # Minor version bump
            else:
                severity = 'low'  # Patch version bump
            
            update = {
                'name': dep,
                'current_version': current_version,
                'latest_version': latest_version,
                'severity': severity,
                'tier': random.choice(['tier1', 'tier2', 'tier3', 'tier4']),
                'type': random.choice(['python', 'npm', 'docker']),
                'vulnerabilities': [],
                'impact': 'Performance improvements and bug fixes',
                'migration_required': False
            }
            
            # Add vulnerabilities to some updates
            if random.random() < 0.3:  # 30% chance of vulnerabilities
                vuln_template = random.choice(self.cve_templates)
                vuln = vuln_template.copy()
                vuln['id'] = vuln['id'].format(rand=f"{random.randint(1000, 9999)}")
                vuln['package'] = vuln['package'].format(dep=dep)
                vuln['version'] = vuln['version'].format(version=current_version)
                update['vulnerabilities'] = [vuln]
                
                # Adjust severity based on vulnerability
                if vuln['severity'] == 'critical':
                    update['severity'] = 'critical'
                elif vuln['severity'] == 'high' and update['severity'] != 'critical':
                    update['severity'] = 'high'
            
            updates.append(update)
        
        return updates
    
    def generate_mock_security_findings(self, count: int = 5) -> List[Dict[str, Any]]:
        """Generate mock security findings."""
        findings = []
        
        for i in range(count):
            template = random.choice(self.cve_templates)
            finding = template.copy()
            finding['id'] = finding['id'].format(rand=f"{random.randint(1000, 9999)}")
            finding['package'] = finding['package'].format(dep=random.choice(self.dependencies))
            finding['version'] = finding['version'].format(version=f"{random.randint(1, 3)}.{random.randint(0, 9)}.{random.randint(0, 9)}")
            
            # Add recommendation
            finding['recommendation'] = f"Update to version {int(finding['version'].split('.')[0]) + 1}.0.0 or later"
            
            findings.append(finding)
        
        return findings
    
    def generate_mock_breaking_changes(self, count: int = 3) -> List[Dict[str, Any]]:
        """Generate mock breaking changes."""
        changes = []
        
        breaking_change_templates = [
            "API signature changes in {dep}",
            "Removed deprecated methods in {dep}",
            "Changed default configuration values in {dep}",
            "Updated authentication mechanism in {dep}",
            "Modified data structures in {dep}"
        ]
        
        for i in range(count):
            dep = random.choice(self.dependencies)
            from_version = f"{random.randint(1, 2)}.{random.randint(0, 9)}.{random.randint(0, 9)}"
            to_version = f"{int(from_version.split('.')[0]) + 1}.0.0"
            
            change = {
                'dependency': dep,
                'from_version': from_version,
                'to_version': to_version,
                'changes': [
                    random.choice(breaking_change_templates).format(dep=dep)
                    for _ in range(random.randint(1, 3))
                ],
                'affected_services': [f"service_{random.randint(1, 10)}" for _ in range(random.randint(1, 3))],
                'migration_required': True,
                'estimated_effort': f"{random.randint(1, 8)} hours"
            }
            
            changes.append(change)
        
        return changes
    
    def generate_mock_system_health(self) -> Dict[str, Any]:
        """Generate mock system health data."""
        monitoring_systems = [
            'github_actions', 'renovate', 'dependabot', 'bandit', 
            'prometheus', 'grafana', 'elasticsearch'
        ]
        
        return {
            'monitoring_systems': {
                system: random.choice(['operational', 'degraded', 'maintenance'])
                for system in monitoring_systems
            },
            'uptime_percentage': round(random.uniform(99.0, 100.0), 2),
            'average_response_time_ms': random.randint(50, 500),
            'failed_scans': random.randint(0, 5),
            'successful_scans': random.randint(20, 50),
            'last_scan': datetime.now().isoformat()
        }
    
    def save_mock_data(self, data: Any, filename: str) -> str:
        """Save mock data to file."""
        filepath = os.path.join(self.data_dir, filename)
        
        try:
            if isinstance(data, pd.DataFrame):
                data.to_csv(filepath, index=False)
            else:
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2)
            
            logger.info(f"Mock data saved to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error saving mock data: {e}")
            return ""
    
    def generate_comprehensive_test_dataset(self) -> Dict[str, Any]:
        """Generate comprehensive mock dataset for testing."""
        dataset = {
            'generated_at': datetime.now().isoformat(),
            'market_data': {},
            'dependency_updates': self.generate_mock_dependency_updates(15),
            'security_findings': self.generate_mock_security_findings(8),
            'breaking_changes': self.generate_mock_breaking_changes(4),
            'system_health': self.generate_mock_system_health(),
            'summary': {
                'total_dependencies': len(self.dependencies),
                'updates_available': 15,
                'critical_updates': len([u for u in self.generate_mock_dependency_updates(15) if u['severity'] == 'critical']),
                'security_vulnerabilities': 8,
                'breaking_changes': 4
            }
        }
        
        # Generate market data for symbols
        for symbol in self.symbols[:3]:  # Generate for first 3 symbols
            dataset['market_data'][symbol] = self.generate_mock_market_data(symbol, 30)
        
        return dataset

def main():
    """Main function to generate mock test data."""
    print("Generating Mock Test Data...")
    
    generator = MockDataGenerator()
    
    # Generate comprehensive dataset
    print("\n=== GENERATING COMPREHENSIVE TEST DATASET ===")
    dataset = generator.generate_comprehensive_test_dataset()
    
    # Save individual components
    print("\n=== SAVING MOCK DATA COMPONENTS ===")
    
    # Save dependency updates
    updates_file = generator.save_mock_data(
        dataset['dependency_updates'], 
        'mock_dependency_updates.json'
    )
    print(f"Dependency updates saved to: {updates_file}")
    
    # Save security findings
    findings_file = generator.save_mock_data(
        dataset['security_findings'], 
        'mock_security_findings.json'
    )
    print(f"Security findings saved to: {findings_file}")
    
    # Save breaking changes
    changes_file = generator.save_mock_data(
        dataset['breaking_changes'], 
        'mock_breaking_changes.json'
    )
    print(f"Breaking changes saved to: {changes_file}")
    
    # Save system health
    health_file = generator.save_mock_data(
        dataset['system_health'], 
        'mock_system_health.json'
    )
    print(f"System health saved to: {health_file}")
    
    # Save market data
    for symbol, data in dataset['market_data'].items():
        market_file = generator.save_mock_data(
            data, 
            f'mock_market_data_{symbol}.csv'
        )
        print(f"Market data for {symbol} saved to: {market_file}")
    
    # Save complete dataset
    complete_file = generator.save_mock_data(
        dataset, 
        'mock_test_dataset.json'
    )
    print(f"Complete dataset saved to: {complete_file}")
    
    # Show summary
    print("\n=== MOCK DATA SUMMARY ===")
    summary = dataset['summary']
    print(f"Total Dependencies: {summary['total_dependencies']}")
    print(f"Updates Available: {summary['updates_available']}")
    print(f"Critical Updates: {summary['critical_updates']}")
    print(f"Security Vulnerabilities: {summary['security_vulnerabilities']}")
    print(f"Breaking Changes: {summary['breaking_changes']}")
    print(f"Symbols with Market Data: {len(dataset['market_data'])}")
    
    print("\nMock test data generation completed.")
    return 0

if __name__ == "__main__":
    sys.exit(main())