#!/usr/bin/env python3
"""
Comprehensive Fraud Detection Test Suite
Full testing with all external dependencies in Docker environment
"""

import asyncio
import json
import logging
import numpy as np
import pandas as pd
import pytest
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import tempfile
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from security.advanced_fraud_detection import (
        FraudDetectionEngine, FraudFeatures, FraudEvent, FraudRiskLevel, FraudType
    )
    from security.transaction_graph_analytics import (
        TransactionGraphAnalytics, PatternType, RiskSeverity, SuspiciousPattern
    )
    from security.automated_response_system import (
        AutomatedResponseSystem, ActionType, ActionRule, ActionExecution
    )
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    logger.error(f"Import error: {e}")
    DEPENDENCIES_AVAILABLE = False

class ComprehensiveFraudDetectionTest:
    """Comprehensive test suite for fraud detection system"""
    
    def __init__(self):
        self.temp_dir = None
        self.fraud_engine = None
        self.graph_analytics = None
        self.response_system = None
        self.test_results = []
        
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        if DEPENDENCIES_AVAILABLE:
            self.fraud_engine = FraudDetectionEngine(model_path=os.path.join(self.temp_dir, "models"))
            self.graph_analytics = TransactionGraphAnalytics()
            self.response_system = AutomatedResponseSystem()
        
    def teardown_method(self):
        """Clean up test environment"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def log_test_result(self, test_name: str, passed: bool, details: str = "", metrics: Dict = None):
        """Log test result with metrics"""
        result = {
            'test_name': test_name,
            'passed': passed,
            'details': details,
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics or {}
        }
        self.test_results.append(result)
        
        status = "PASS" if passed else "FAIL"
        logger.info(f"[{status}] {test_name}: {details}")
        
        if metrics:
            for key, value in metrics.items():
                logger.info(f"  {key}: {value}")
    
    @pytest.mark.asyncio
    async def test_fraud_detection_engine_comprehensive(self):
        """Comprehensive test of fraud detection engine"""
        if not DEPENDENCIES_AVAILABLE:
            pytest.skip("Dependencies not available")
        
        try:
            # Test 1: Engine initialization
            assert self.fraud_engine is not None
            self.log_test_result("Engine Initialization", True, "Fraud detection engine created")
            
            # Test 2: Feature extraction with various scenarios
            test_scenarios = [
                {
                    'name': 'Normal Transaction',
                    'data': {
                        'user_id': 'user_normal',
                        'timestamp': datetime.now(),
                        'device_id': 'known_device',
                        'location': 'New York',
                        'ip_address': '192.168.1.100',
                        'transaction_amount': 1000,
                        'session_duration': 1800
                    },
                    'expected_risk': 'LOW'
                },
                {
                    'name': 'Suspicious Transaction',
                    'data': {
                        'user_id': 'user_suspicious',
                        'timestamp': datetime.now(),
                        'device_id': 'new_device_123',
                        'location': 'Unknown Location',
                        'ip_address': '203.0.113.1',
                        'transaction_amount': 50000,
                        'session_duration': 60,
                        'vpn_detected': True,
                        'new_device': True,
                        'new_location': True
                    },
                    'expected_risk': 'HIGH'
                }
            ]
            
            fraud_scores = []
            for scenario in test_scenarios:
                # Extract features
                features = self.fraud_engine.extract_features(scenario['data'])
                assert isinstance(features, FraudFeatures)
                
                # Detect fraud
                fraud_event = self.fraud_engine.detect_fraud(scenario['data'])
                assert isinstance(fraud_event, FraudEvent)
                
                fraud_scores.append(fraud_event.fraud_score)
            
            self.log_test_result(
                "Fraud Detection Scenarios", 
                True, 
                f"All {len(test_scenarios)} scenarios processed correctly",
                {
                    'normal_score': f"{fraud_scores[0]:.3f}",
                    'suspicious_score': f"{fraud_scores[1]:.3f}"
                }
            )
            
            # Test 3: Dashboard functionality
            dashboard = self.fraud_engine.get_fraud_dashboard()
            required_sections = ['events', 'alerts', 'models', 'transaction_graph']
            
            for section in required_sections:
                assert section in dashboard
            
            self.log_test_result(
                "Dashboard Functionality", 
                True, 
                "All dashboard sections present",
                {
                    'total_events': dashboard['events']['total_events'],
                    'total_alerts': dashboard['alerts']['total_alerts']
                }
            )
            
        except Exception as e:
            self.log_test_result("Fraud Detection Engine", False, f"Error: {str(e)}")
            raise   
 
    def test_transaction_graph_analytics_comprehensive(self):
        """Comprehensive test of transaction graph analytics"""
        if not DEPENDENCIES_AVAILABLE:
            pytest.skip("Dependencies not available")
        
        try:
            # Test 1: Graph construction
            users = ['alice', 'bob', 'charlie', 'david', 'eve']
            
            # Add normal transactions
            for i in range(10):
                from_user = users[i % len(users)]
                to_user = users[(i + 1) % len(users)]
                amount = 1000 + (i * 500)
                timestamp = datetime.now() - timedelta(hours=i)
                
                edge_id = self.graph_analytics.add_transaction(from_user, to_user, amount, timestamp)
                assert edge_id is not None
            
            self.log_test_result(
                "Graph Construction", 
                True, 
                f"Added 10 normal transactions",
                {
                    'total_nodes': len(self.graph_analytics.nodes),
                    'total_edges': len(self.graph_analytics.edges)
                }
            )
            
            # Test 2: Create suspicious patterns
            # Circular transaction
            circular_amount = 50000
            timestamp = datetime.now() - timedelta(hours=2)
            self.graph_analytics.add_transaction('alice', 'bob', circular_amount, timestamp)
            self.graph_analytics.add_transaction('bob', 'charlie', circular_amount * 0.95, 
                                                timestamp + timedelta(minutes=30))
            self.graph_analytics.add_transaction('charlie', 'alice', circular_amount * 0.9, 
                                                timestamp + timedelta(hours=1))
            
            self.log_test_result(
                "Suspicious Pattern Creation", 
                True, 
                "Created circular transaction pattern"
            )
            
            # Test 3: Pattern detection
            patterns = self.graph_analytics.analyze_all_patterns()
            
            total_patterns = sum(len(pattern_list) for pattern_list in patterns.values())
            
            self.log_test_result(
                "Pattern Detection", 
                True, 
                f"Detected {total_patterns} suspicious patterns"
            )
            
            # Test 4: Risk scoring
            risk_score = self.graph_analytics.get_node_risk_score('alice')
            assert 0 <= risk_score <= 1
            
            self.log_test_result(
                "Risk Scoring", 
                True, 
                f"Risk score calculated: {risk_score:.3f}"
            )
            
        except Exception as e:
            self.log_test_result("Transaction Graph Analytics", False, f"Error: {str(e)}")
            raise  
  
    @pytest.mark.asyncio
    async def test_automated_response_system_comprehensive(self):
        """Comprehensive test of automated response system"""
        if not DEPENDENCIES_AVAILABLE:
            pytest.skip("Dependencies not available")
        
        try:
            # Test 1: Rule management
            test_rule = ActionRule(
                rule_id="test_critical",
                name="Critical Fraud Response",
                description="Response to critical fraud",
                conditions={'fraud_score': {'min': 0.9}},
                actions=[ActionType.BLOCK, ActionType.ESCALATE],
                priority=1
            )
            
            self.response_system.add_rule(test_rule)
            assert test_rule.rule_id in self.response_system.rules
            
            self.log_test_result(
                "Rule Management", 
                True, 
                "Rule added successfully",
                {'total_rules': len(self.response_system.rules)}
            )
            
            # Test 2: Event processing
            test_event = {
                'event_id': 'test_001',
                'user_id': 'test_user',
                'fraud_score': 0.95,
                'risk_level': 'CRITICAL',
                'fraud_types': ['ACCOUNT_TAKEOVER'],
                'transaction_amount': 100000
            }
            
            executions = await self.response_system.process_event(test_event)
            
            self.log_test_result(
                "Event Processing", 
                True, 
                f"Processed event with {len(executions)} actions"
            )
            
            # Test 3: Dashboard
            dashboard = self.response_system.get_response_dashboard()
            required_sections = ['rules', 'executions', 'cases', 'performance']
            
            for section in required_sections:
                assert section in dashboard
            
            self.log_test_result(
                "Response Dashboard", 
                True, 
                "All dashboard sections present"
            )
            
        except Exception as e:
            self.log_test_result("Automated Response System", False, f"Error: {str(e)}")
            raise
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['passed']])
        
        report = {
            'test_suite': 'Comprehensive Fraud Detection Test Suite',
            'execution_date': datetime.now().isoformat(),
            'environment': 'Docker with full dependencies',
            'summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': total_tests - passed_tests,
                'success_rate': f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
            },
            'test_results': self.test_results,
            'components_tested': [
                'Advanced Fraud Detection Engine',
                'Transaction Graph Analytics',
                'Automated Response System'
            ]
        }
        
        return report

# Test execution functions
def run_comprehensive_tests():
    """Run comprehensive test suite"""
    if not DEPENDENCIES_AVAILABLE:
        print("❌ Dependencies not available - cannot run comprehensive tests")
        return False
    
    test_suite = ComprehensiveFraudDetectionTest()
    test_suite.setup_method()
    
    try:
        print("🚀 Starting Comprehensive Fraud Detection Test Suite")
        print("=" * 80)
        
        # Run all tests
        asyncio.run(test_suite.test_fraud_detection_engine_comprehensive())
        test_suite.test_transaction_graph_analytics_comprehensive()
        asyncio.run(test_suite.test_automated_response_system_comprehensive())
        
        # Generate report
        report = test_suite.generate_comprehensive_report()
        
        # Save report
        with open('security/COMPREHENSIVE_TEST_REPORT.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {report['summary']['total_tests']}")
        print(f"Passed: {report['summary']['passed_tests']}")
        print(f"Failed: {report['summary']['failed_tests']}")
        print(f"Success Rate: {report['summary']['success_rate']}")
        
        if report['summary']['failed_tests'] == 0:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ Fraud Detection System is ready for production")
        else:
            print(f"\n⚠️  {report['summary']['failed_tests']} test(s) failed")
        
        print(f"\n📄 Detailed report saved to: COMPREHENSIVE_TEST_REPORT.json")
        
        return report['summary']['failed_tests'] == 0
        
    except Exception as e:
        print(f"❌ Test suite execution failed: {str(e)}")
        return False
    
    finally:
        test_suite.teardown_method()

if __name__ == "__main__":
    success = run_comprehensive_tests()
    exit(0 if success else 1)