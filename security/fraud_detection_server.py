#!/usr/bin/env python3
"""
Fraud Detection Server
Simple HTTP server for testing fraud detection capabilities
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any
import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FraudDetectionServer:
    """Simple fraud detection server for testing"""
    
    def __init__(self):
        self.fraud_engine = None
        self.graph_analytics = None
        self.response_system = None
        self.initialize_components()
    
    def initialize_components(self):
        """Initialize fraud detection components"""
        try:
            from security.advanced_fraud_detection import FraudDetectionEngine
            from security.transaction_graph_analytics import TransactionGraphAnalytics
            from security.automated_response_system import AutomatedResponseSystem
            
            self.fraud_engine = FraudDetectionEngine()
            self.graph_analytics = TransactionGraphAnalytics()
            self.response_system = AutomatedResponseSystem()
            
            logger.info("✅ All fraud detection components initialized successfully")
            
        except ImportError as e:
            logger.error(f"❌ Failed to import components: {e}")
            logger.info("Running in mock mode without external dependencies")
    
    async def process_fraud_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process fraud detection request"""
        try:
            if self.fraud_engine:
                # Real fraud detection
                fraud_event = self.fraud_engine.detect_fraud(request_data)
                
                response = {
                    'status': 'success',
                    'fraud_score': fraud_event.fraud_score,
                    'risk_level': fraud_event.risk_level.value,
                    'fraud_types': [ft.value for ft in fraud_event.fraud_types],
                    'confidence': fraud_event.confidence,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Process with response system if high risk
                if fraud_event.fraud_score > 0.7:
                    response_event = {
                        'event_id': fraud_event.event_id,
                        'user_id': fraud_event.user_id,
                        'fraud_score': fraud_event.fraud_score,
                        'risk_level': fraud_event.risk_level.value
                    }
                    
                    executions = await self.response_system.process_event(response_event)
                    response['actions_taken'] = [e.action_type.value for e in executions]
                
            else:
                # Mock response
                response = {
                    'status': 'mock',
                    'fraud_score': 0.5,
                    'risk_level': 'MEDIUM',
                    'fraud_types': ['TRANSACTION_FRAUD'],
                    'confidence': 0.7,
                    'timestamp': datetime.now().isoformat(),
                    'message': 'Running in mock mode - install dependencies for full functionality'
                }
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing fraud request: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'components': {
                'fraud_engine': self.fraud_engine is not None,
                'graph_analytics': self.graph_analytics is not None,
                'response_system': self.response_system is not None
            },
            'mode': 'production' if all([
                self.fraud_engine, 
                self.graph_analytics, 
                self.response_system
            ]) else 'mock'
        }
        
        if self.fraud_engine:
            dashboard = self.fraud_engine.get_fraud_dashboard()
            status['metrics'] = {
                'total_events': dashboard['events']['total_events'],
                'total_alerts': dashboard['alerts']['total_alerts']
            }
        
        return status
    
    async def run_server(self, host: str = '0.0.0.0', port: int = 8080):
        """Run the fraud detection server"""
        logger.info(f"🚀 Starting Fraud Detection Server on {host}:{port}")
        
        # Simple HTTP server simulation
        while True:
            try:
                # Simulate processing requests
                test_request = {
                    'user_id': 'test_user',
                    'timestamp': datetime.now(),
                    'transaction_amount': 25000,
                    'device_id': 'test_device',
                    'location': 'Test Location',
                    'ip_address': '192.168.1.100'
                }
                
                response = await self.process_fraud_request(test_request)
                logger.info(f"Processed test request - Fraud Score: {response.get('fraud_score', 'N/A')}")
                
                # Get system status
                status = self.get_system_status()
                logger.info(f"System Status: {status['mode']} mode")
                
                # Wait before next iteration
                await asyncio.sleep(30)
                
            except KeyboardInterrupt:
                logger.info("🛑 Server shutdown requested")
                break
            except Exception as e:
                logger.error(f"Server error: {e}")
                await asyncio.sleep(5)

def main():
    """Main server function"""
    server = FraudDetectionServer()
    
    try:
        asyncio.run(server.run_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server failed: {e}")

if __name__ == "__main__":
    main()