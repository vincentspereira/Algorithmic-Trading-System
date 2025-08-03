#!/usr/bin/env python3
"""
Docker-based Fraud Detection Validation
Simplified test that works with Docker environment
"""

import asyncio
import json
import logging
import numpy as np
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
import tempfile
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class DockerFraudDetectionValidator:
    """Docker-based fraud detection validator"""
    
    def __init__(self):
        self.test_results = []
        self.temp_dir = None
        
    def log_test(self, test_name: str, passed: bool, details: str = "", metrics: Dict = None):
        """Log test result"""
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
    
    def test_dependencies(self):
        """Test that all required dependencies are available"""
        try:
            import numpy
            import pandas
            import sklearn
            import networkx
            import matplotlib
            import seaborn
            
            self.log_test(
                "Dependencies Check", 
                True, 
                "All required dependencies available",
                {
                    'numpy_version': numpy.__version__,
                    'pandas_version': pandas.__version__,
                    'sklearn_version': sklearn.__version__,
                    'networkx_version': networkx.__version__
                }
            )
            return True
            
        except ImportError as e:
            self.log_test("Dependencies Check", False, f"Missing dependency: {e}")
            return False
    
    def test_fraud_detection_import(self):
        """Test fraud detection module imports"""
        try:
            # Test basic imports without email dependencies
            sys.path.append('/app')
            
            # Create a mock email module to avoid import issues
            import types
            mock_email = types.ModuleType('email')
            mock_mime = types.ModuleType('mime')
            mock_text = types.ModuleType('text')
            mock_multipart = types.ModuleType('multipart')
            
            # Create mock classes
            class MockMimeText:
                def __init__(self, *args, **kwargs):
                    pass
                def attach(self, *args):
                    pass
            
            class MockMimeMultipart:
                def __init__(self, *args, **kwargs):
                    self.items = {}
                def __setitem__(self, key, value):
                    self.items[key] = value
                def attach(self, *args):
                    pass
            
            mock_text.MimeText = MockMimeText
            mock_multipart.MimeMultipart = MockMimeMultipart
            mock_mime.text = mock_text
            mock_mime.multipart = mock_multipart
            mock_email.mime = mock_mime
            
            sys.modules['email'] = mock_email
            sys.modules['email.mime'] = mock_mime
            sys.modules['email.mime.text'] = mock_text
            sys.modules['email.mime.multipart'] = mock_multipart
            
            # Now try to import our modules
            from security.advanced_fraud_detection import FraudDetectionEngine, FraudFeatures
            from security.transaction_graph_analytics import TransactionGraphAnalytics
            
            self.log_test("Module Imports", True, "Successfully imported fraud detection modules")
            return True
            
        except Exception as e:
            self.log_test("Module Imports", False, f"Import error: {e}")
            return False
    
    def test_fraud_detection_basic(self):
        """Test basic fraud detection functionality"""
        try:
            from security.advanced_fraud_detection import FraudDetectionEngine, FraudFeatures
            
            # Initialize engine
            self.temp_dir = tempfile.mkdtemp()
            engine = FraudDetectionEngine(model_path=os.path.join(self.temp_dir, "models"))
            
            # Test feature extraction
            test_data = {
                'user_id': 'test_user',
                'timestamp': datetime.now(),
                'device_id': 'test_device',
                'location': 'Test Location',
                'ip_address': '192.168.1.100',
                'transaction_amount': 25000,
                'session_duration': 300
            }
            
            features = engine.extract_features(test_data)
            assert isinstance(features, FraudFeatures)
            
            # Test fraud detection
            fraud_event = engine.detect_fraud(test_data)
            assert fraud_event is not None
            assert hasattr(fraud_event, 'fraud_score')
            assert 0 <= fraud_event.fraud_score <= 1
            
            # Test dashboard
            dashboard = engine.get_fraud_dashboard()
            assert isinstance(dashboard, dict)
            assert 'events' in dashboard
            
            self.log_test(
                "Fraud Detection Basic", 
                True, 
                "Basic fraud detection working",
                {
                    'fraud_score': f"{fraud_event.fraud_score:.3f}",
                    'risk_level': fraud_event.risk_level.value,
                    'total_events': dashboard['events']['total_events']
                }
            )
            return True
            
        except Exception as e:
            self.log_test("Fraud Detection Basic", False, f"Error: {e}")
            return False
    
    def test_graph_analytics_basic(self):
        """Test basic graph analytics functionality"""
        try:
            from security.transaction_graph_analytics import TransactionGraphAnalytics
            
            # Initialize graph analytics
            graph = TransactionGraphAnalytics()
            
            # Add test transactions
            users = ['alice', 'bob', 'charlie']
            for i in range(5):
                from_user = users[i % len(users)]
                to_user = users[(i + 1) % len(users)]
                amount = 1000 + (i * 500)
                timestamp = datetime.now() - timedelta(hours=i)
                
                edge_id = graph.add_transaction(from_user, to_user, amount, timestamp)
                assert edge_id is not None
            
            # Test pattern detection
            patterns = graph.analyze_all_patterns()
            assert isinstance(patterns, dict)
            
            # Test risk scoring
            risk_score = graph.get_node_risk_score('alice')
            assert 0 <= risk_score <= 1
            
            # Test analytics summary
            summary = graph.get_analytics_summary()
            assert isinstance(summary, dict)
            assert 'graph_statistics' in summary
            
            self.log_test(
                "Graph Analytics Basic", 
                True, 
                "Basic graph analytics working",
                {
                    'total_nodes': len(graph.nodes),
                    'total_edges': len(graph.edges),
                    'alice_risk_score': f"{risk_score:.3f}",
                    'total_patterns': sum(len(p) for p in patterns.values())
                }
            )
            return True
            
        except Exception as e:
            self.log_test("Graph Analytics Basic", False, f"Error: {e}")
            return False
    
    def test_performance_basic(self):
        """Test basic performance metrics"""
        try:
            from security.advanced_fraud_detection import FraudDetectionEngine
            import time
            
            # Initialize engine
            engine = FraudDetectionEngine(model_path=os.path.join(self.temp_dir, "models"))
            
            # Performance test
            start_time = time.time()
            
            for i in range(10):
                test_data = {
                    'user_id': f'perf_user_{i}',
                    'timestamp': datetime.now(),
                    'device_id': f'device_{i}',
                    'location': 'Test Location',
                    'ip_address': f'192.168.1.{i}',
                    'transaction_amount': 1000 + (i * 100),
                    'session_duration': 300 + (i * 10)
                }
                
                fraud_event = engine.detect_fraud(test_data)
                assert fraud_event is not None
            
            total_time = time.time() - start_time
            avg_time = total_time / 10
            
            # Should process at least 1 event per second
            assert avg_time < 1.0
            
            self.log_test(
                "Performance Basic", 
                True, 
                "Performance requirements met",
                {
                    'total_time_seconds': f"{total_time:.3f}",
                    'avg_time_per_event_ms': f"{avg_time * 1000:.1f}",
                    'throughput_per_second': f"{1/avg_time:.1f}"
                }
            )
            return True
            
        except Exception as e:
            self.log_test("Performance Basic", False, f"Error: {e}")
            return False
    
    def cleanup(self):
        """Clean up test environment"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def run_all_tests(self):
        """Run all validation tests"""
        print("🐳 Docker-based Fraud Detection Validation")
        print("=" * 60)
        
        try:
            # Run tests
            deps_ok = self.test_dependencies()
            if not deps_ok:
                print("❌ Dependencies not available - cannot continue")
                return False
            
            imports_ok = self.test_fraud_detection_import()
            if not imports_ok:
                print("❌ Module imports failed - cannot continue")
                return False
            
            self.test_fraud_detection_basic()
            self.test_graph_analytics_basic()
            self.test_performance_basic()
            
            # Generate summary
            total_tests = len(self.test_results)
            passed_tests = len([r for r in self.test_results if r['passed']])
            failed_tests = total_tests - passed_tests
            
            print("\n" + "=" * 60)
            print("VALIDATION SUMMARY")
            print("=" * 60)
            print(f"Total Tests: {total_tests}")
            print(f"Passed: {passed_tests}")
            print(f"Failed: {failed_tests}")
            print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
            
            if failed_tests == 0:
                print("\n🎉 ALL TESTS PASSED!")
                print("✅ Fraud Detection System validated in Docker environment")
            else:
                print(f"\n⚠️  {failed_tests} test(s) failed")
                if passed_tests >= total_tests * 0.8:
                    print("✅ System is substantially working")
                else:
                    print("❌ System needs attention")
            
            # Generate report
            report = {
                'validation_suite': 'Docker-based Fraud Detection Validation',
                'execution_date': datetime.now().isoformat(),
                'environment': 'Docker with full dependencies',
                'summary': {
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'failed_tests': failed_tests,
                    'success_rate': f"{(passed_tests/total_tests)*100:.1f}%"
                },
                'test_results': self.test_results,
                'status': 'PASSED' if failed_tests == 0 else 'PARTIALLY_PASSED' if passed_tests >= total_tests * 0.8 else 'FAILED'
            }
            
            # Save report
            with open('/app/security/DOCKER_VALIDATION_REPORT.json', 'w') as f:
                json.dump(report, f, indent=2)
            
            print(f"\n📄 Validation report saved to: DOCKER_VALIDATION_REPORT.json")
            
            return failed_tests == 0
            
        except Exception as e:
            print(f"❌ Validation failed: {e}")
            return False
        
        finally:
            self.cleanup()

def main():
    """Main validation function"""
    validator = DockerFraudDetectionValidator()
    success = validator.run_all_tests()
    exit(0 if success else 1)

if __name__ == "__main__":
    main()