"""
Webhook Management Interface
Provides REST API endpoints for managing webhook endpoints and monitoring deliveries.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from flask import Flask, request, jsonify, Blueprint
from dataclasses import asdict
import asyncio
import json

from nautilus_trader_engine.events.webhook_system import (
    WebhookEventSystem, WebhookEndpoint, WebhookEventType, 
    WebhookSecurityType, WebhookStatus, create_webhook_system
)

class WebhookManagementAPI:
    """Webhook management REST API"""
    
    def __init__(self, webhook_system: WebhookEventSystem, app: Flask = None):
        self.webhook_system = webhook_system
        self.app = app or Flask(__name__)
        self.logger = logging.getLogger(__name__)
        
        # Create blueprint for webhook management
        self.blueprint = Blueprint('webhook_management', __name__, url_prefix='/api/v1/webhooks')
        self._setup_routes()
        
        # Register blueprint
        self.app.register_blueprint(self.blueprint)
    
    def _setup_routes(self):
        """Setup webhook management routes"""
        
        @self.blueprint.route('/', methods=['GET'])
        def list_endpoints():
            """List all webhook endpoints"""
            try:
                endpoints = self.webhook_system.list_endpoints()
                return jsonify({
                    'success': True,
                    'data': [self._serialize_endpoint(endpoint) for endpoint in endpoints],
                    'count': len(endpoints)
                })
            except Exception as e:
                self.logger.error(f"Error listing endpoints: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.blueprint.route('/', methods=['POST'])
        def create_endpoint():
            """Create new webhook endpoint"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        'success': False,
                        'error': 'Request body is required'
                    }), 400
                
                # Validate required fields
                required_fields = ['url', 'name']
                for field in required_fields:
                    if field not in data:
                        return jsonify({
                            'success': False,
                            'error': f'Field "{field}" is required'
                        }), 400
                
                # Parse event types
                events = []
                if 'events' in data:
                    for event_str in data['events']:
                        try:
                            events.append(WebhookEventType(event_str))
                        except ValueError:
                            return jsonify({
                                'success': False,
                                'error': f'Invalid event type: {event_str}'
                            }), 400
                
                # Parse security type
                security_type = WebhookSecurityType.NONE
                if 'security_type' in data:
                    try:
                        security_type = WebhookSecurityType(data['security_type'])
                    except ValueError:
                        return jsonify({
                            'success': False,
                            'error': f'Invalid security type: {data["security_type"]}'
                        }), 400
                
                # Create endpoint
                endpoint = WebhookEndpoint(
                    id="",  # Will be generated
                    url=data['url'],
                    name=data['name'],
                    description=data.get('description', ''),
                    events=events,
                    security_type=security_type,
                    secret=data.get('secret'),
                    headers=data.get('headers', {}),
                    timeout=data.get('timeout', 30),
                    max_retries=data.get('max_retries', 3),
                    retry_delay=data.get('retry_delay', 5),
                    is_active=data.get('is_active', True)
                )
                
                endpoint_id = self.webhook_system.register_endpoint(endpoint)
                endpoint.id = endpoint_id
                
                return jsonify({
                    'success': True,
                    'data': self._serialize_endpoint(endpoint),
                    'message': f'Webhook endpoint created with ID: {endpoint_id}'
                }), 201
                
            except Exception as e:
                self.logger.error(f"Error creating endpoint: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.blueprint.route('/<endpoint_id>', methods=['GET'])
        def get_endpoint(endpoint_id: str):
            """Get webhook endpoint by ID"""
            try:
                endpoint = self.webhook_system.get_endpoint(endpoint_id)
                if not endpoint:
                    return jsonify({
                        'success': False,
                        'error': 'Endpoint not found'
                    }), 404
                
                return jsonify({
                    'success': True,
                    'data': self._serialize_endpoint(endpoint)
                })
                
            except Exception as e:
                self.logger.error(f"Error getting endpoint: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.blueprint.route('/<endpoint_id>', methods=['PUT'])
        def update_endpoint(endpoint_id: str):
            """Update webhook endpoint"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        'success': False,
                        'error': 'Request body is required'
                    }), 400
                
                # Check if endpoint exists
                endpoint = self.webhook_system.get_endpoint(endpoint_id)
                if not endpoint:
                    return jsonify({
                        'success': False,
                        'error': 'Endpoint not found'
                    }), 404
                
                # Parse event types if provided
                if 'events' in data:
                    events = []
                    for event_str in data['events']:
                        try:
                            events.append(WebhookEventType(event_str))
                        except ValueError:
                            return jsonify({
                                'success': False,
                                'error': f'Invalid event type: {event_str}'
                            }), 400
                    data['events'] = events
                
                # Parse security type if provided
                if 'security_type' in data:
                    try:
                        data['security_type'] = WebhookSecurityType(data['security_type'])
                    except ValueError:
                        return jsonify({
                            'success': False,
                            'error': f'Invalid security type: {data["security_type"]}'
                        }), 400
                
                # Update endpoint
                success = self.webhook_system.update_endpoint(endpoint_id, **data)
                if not success:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to update endpoint'
                    }), 500
                
                # Get updated endpoint
                updated_endpoint = self.webhook_system.get_endpoint(endpoint_id)
                
                return jsonify({
                    'success': True,
                    'data': self._serialize_endpoint(updated_endpoint),
                    'message': 'Endpoint updated successfully'
                })
                
            except Exception as e:
                self.logger.error(f"Error updating endpoint: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.blueprint.route('/<endpoint_id>', methods=['DELETE'])
        def delete_endpoint(endpoint_id: str):
            """Delete webhook endpoint"""
            try:
                success = self.webhook_system.unregister_endpoint(endpoint_id)
                if not success:
                    return jsonify({
                        'success': False,
                        'error': 'Endpoint not found'
                    }), 404
                
                return jsonify({
                    'success': True,
                    'message': 'Endpoint deleted successfully'
                })
                
            except Exception as e:
                self.logger.error(f"Error deleting endpoint: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.blueprint.route('/<endpoint_id>/test', methods=['POST'])
        def test_endpoint(endpoint_id: str):
            """Test webhook endpoint with sample event"""
            try:
                endpoint = self.webhook_system.get_endpoint(endpoint_id)
                if not endpoint:
                    return jsonify({
                        'success': False,
                        'error': 'Endpoint not found'
                    }), 404
                
                # Get test data from request or use default
                data = request.get_json() or {}
                test_data = data.get('test_data', {
                    'test': True,
                    'message': 'This is a test webhook event',
                    'timestamp': datetime.now().isoformat()
                })
                
                # Emit test event
                event_id = asyncio.run(
                    self.webhook_system.emit_event(
                        WebhookEventType.CUSTOM_EVENT,
                        test_data,
                        metadata={'test': True}
                    )
                )
                
                return jsonify({
                    'success': True,
                    'event_id': event_id,
                    'message': 'Test event sent successfully'
                })
                
            except Exception as e:
                self.logger.error(f"Error testing endpoint: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.blueprint.route('/<endpoint_id>/stats', methods=['GET'])
        def get_endpoint_stats(endpoint_id: str):
            """Get delivery statistics for endpoint"""
            try:
                endpoint = self.webhook_system.get_endpoint(endpoint_id)
                if not endpoint:
                    return jsonify({
                        'success': False,
                        'error': 'Endpoint not found'
                    }), 404
                
                stats = self.webhook_system.get_delivery_stats(endpoint_id)
                
                return jsonify({
                    'success': True,
                    'data': {
                        'endpoint_id': endpoint_id,
                        'endpoint_name': endpoint.name,
                        'stats': stats,
                        'endpoint_stats': {
                            'success_count': endpoint.success_count,
                            'failure_count': endpoint.failure_count,
                            'last_success': endpoint.last_success.isoformat() if endpoint.last_success else None,
                            'last_failure': endpoint.last_failure.isoformat() if endpoint.last_failure else None
                        }
                    }
                })
                
            except Exception as e:
                self.logger.error(f"Error getting endpoint stats: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.blueprint.route('/<endpoint_id>/deliveries', methods=['GET'])
        def get_endpoint_deliveries(endpoint_id: str):
            """Get recent deliveries for endpoint"""
            try:
                endpoint = self.webhook_system.get_endpoint(endpoint_id)
                if not endpoint:
                    return jsonify({
                        'success': False,
                        'error': 'Endpoint not found'
                    }), 404
                
                limit = request.args.get('limit', 50, type=int)
                deliveries = self.webhook_system.get_recent_deliveries(endpoint_id, limit)
                
                return jsonify({
                    'success': True,
                    'data': [self._serialize_delivery(delivery) for delivery in deliveries],
                    'count': len(deliveries)
                })
                
            except Exception as e:
                self.logger.error(f"Error getting endpoint deliveries: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.blueprint.route('/events', methods=['GET'])
        def list_event_types():
            """List available webhook event types"""
            try:
                event_types = [
                    {
                        'value': event_type.value,
                        'name': event_type.name,
                        'description': self._get_event_description(event_type)
                    }
                    for event_type in WebhookEventType
                ]
                
                return jsonify({
                    'success': True,
                    'data': event_types,
                    'count': len(event_types)
                })
                
            except Exception as e:
                self.logger.error(f"Error listing event types: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.blueprint.route('/events/emit', methods=['POST'])
        def emit_custom_event():
            """Emit custom webhook event"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        'success': False,
                        'error': 'Request body is required'
                    }), 400
                
                event_type_str = data.get('event_type', 'custom.event')
                event_data = data.get('data', {})
                metadata = data.get('metadata', {})
                
                # Parse event type
                try:
                    event_type = WebhookEventType(event_type_str)
                except ValueError:
                    event_type = WebhookEventType.CUSTOM_EVENT
                
                # Emit event
                event_id = asyncio.run(
                    self.webhook_system.emit_event(event_type, event_data, metadata)
                )
                
                return jsonify({
                    'success': True,
                    'event_id': event_id,
                    'message': 'Event emitted successfully'
                })
                
            except Exception as e:
                self.logger.error(f"Error emitting custom event: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.blueprint.route('/stats', methods=['GET'])
        def get_global_stats():
            """Get global webhook delivery statistics"""
            try:
                stats = self.webhook_system.get_delivery_stats()
                
                return jsonify({
                    'success': True,
                    'data': {
                        'global_stats': stats,
                        'endpoint_count': len(self.webhook_system.endpoints),
                        'active_endpoints': len([
                            e for e in self.webhook_system.endpoints.values() 
                            if e.is_active
                        ])
                    }
                })
                
            except Exception as e:
                self.logger.error(f"Error getting global stats: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.blueprint.route('/deliveries', methods=['GET'])
        def get_all_deliveries():
            """Get recent deliveries across all endpoints"""
            try:
                limit = request.args.get('limit', 100, type=int)
                deliveries = self.webhook_system.get_recent_deliveries(limit=limit)
                
                return jsonify({
                    'success': True,
                    'data': [self._serialize_delivery(delivery) for delivery in deliveries],
                    'count': len(deliveries)
                })
                
            except Exception as e:
                self.logger.error(f"Error getting all deliveries: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.blueprint.route('/cleanup', methods=['POST'])
        def cleanup_old_deliveries():
            """Clean up old delivery records"""
            try:
                data = request.get_json() or {}
                days = data.get('days', 7)
                
                cleaned_count = self.webhook_system.cleanup_old_deliveries(days)
                
                return jsonify({
                    'success': True,
                    'cleaned_count': cleaned_count,
                    'message': f'Cleaned up {cleaned_count} old delivery records'
                })
                
            except Exception as e:
                self.logger.error(f"Error cleaning up deliveries: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
    
    def _serialize_endpoint(self, endpoint: WebhookEndpoint) -> Dict[str, Any]:
        """Serialize webhook endpoint for JSON response"""
        data = asdict(endpoint)
        
        # Convert enums to strings
        data['events'] = [event.value for event in endpoint.events]
        data['security_type'] = endpoint.security_type.value
        
        # Convert datetime objects to ISO strings
        data['created_at'] = endpoint.created_at.isoformat()
        data['updated_at'] = endpoint.updated_at.isoformat()
        data['last_success'] = endpoint.last_success.isoformat() if endpoint.last_success else None
        data['last_failure'] = endpoint.last_failure.isoformat() if endpoint.last_failure else None
        
        # Don't expose secrets in responses
        if data.get('secret'):
            data['secret'] = '***HIDDEN***'
        
        return data
    
    def _serialize_delivery(self, delivery) -> Dict[str, Any]:
        """Serialize webhook delivery for JSON response"""
        data = asdict(delivery)
        
        # Convert enums to strings
        data['status'] = delivery.status.value
        
        # Convert datetime objects to ISO strings
        data['created_at'] = delivery.created_at.isoformat()
        data['delivered_at'] = delivery.delivered_at.isoformat() if delivery.delivered_at else None
        data['next_retry_at'] = delivery.next_retry_at.isoformat() if delivery.next_retry_at else None
        
        return data
    
    def _get_event_description(self, event_type: WebhookEventType) -> str:
        """Get description for event type"""
        descriptions = {
            WebhookEventType.ORDER_CREATED: "Triggered when a new order is created",
            WebhookEventType.ORDER_UPDATED: "Triggered when an order is updated",
            WebhookEventType.ORDER_FILLED: "Triggered when an order is filled",
            WebhookEventType.ORDER_CANCELLED: "Triggered when an order is cancelled",
            WebhookEventType.POSITION_OPENED: "Triggered when a new position is opened",
            WebhookEventType.POSITION_UPDATED: "Triggered when a position is updated",
            WebhookEventType.POSITION_CLOSED: "Triggered when a position is closed",
            WebhookEventType.TRADE_EXECUTED: "Triggered when a trade is executed",
            WebhookEventType.PORTFOLIO_UPDATED: "Triggered when portfolio is updated",
            WebhookEventType.RISK_ALERT: "Triggered when a risk alert is generated",
            WebhookEventType.MARKET_DATA_UPDATE: "Triggered when market data is updated",
            WebhookEventType.SYSTEM_ALERT: "Triggered when a system alert occurs",
            WebhookEventType.STRATEGY_SIGNAL: "Triggered when a strategy generates a signal",
            WebhookEventType.BACKTEST_COMPLETED: "Triggered when a backtest is completed",
            WebhookEventType.CUSTOM_EVENT: "Custom user-defined event"
        }
        return descriptions.get(event_type, "No description available")
    
    def run(self, host: str = '0.0.0.0', port: int = 8002, debug: bool = False):
        """Run the webhook management API server"""
        self.logger.info(f"Starting Webhook Management API on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

def create_webhook_management_api(webhook_system: WebhookEventSystem = None) -> WebhookManagementAPI:
    """Create webhook management API"""
    if webhook_system is None:
        webhook_system = create_webhook_system()
    
    return WebhookManagementAPI(webhook_system)

# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def main():
        # Create webhook system
        webhook_system = create_webhook_system()
        await webhook_system.start()
        
        # Create management API
        api = create_webhook_management_api(webhook_system)
        
        # Add health check endpoint
        @api.app.route('/health')
        def health_check():
            return jsonify({
                'status': 'healthy',
                'service': 'Webhook Management API',
                'webhook_system_running': webhook_system.is_running
            })
        
        # Add root endpoint
        @api.app.route('/')
        def index():
            return jsonify({
                'service': 'Nautilus Trader Webhook Management API',
                'version': '1.0',
                'endpoints': {
                    'webhooks': '/api/v1/webhooks',
                    'health': '/health'
                }
            })
        
        print("Webhook Management API is ready!")
        print("Available endpoints:")
        print("- GET /api/v1/webhooks - List all webhook endpoints")
        print("- POST /api/v1/webhooks - Create new webhook endpoint")
        print("- GET /api/v1/webhooks/{id} - Get webhook endpoint")
        print("- PUT /api/v1/webhooks/{id} - Update webhook endpoint")
        print("- DELETE /api/v1/webhooks/{id} - Delete webhook endpoint")
        print("- POST /api/v1/webhooks/{id}/test - Test webhook endpoint")
        print("- GET /api/v1/webhooks/{id}/stats - Get endpoint statistics")
        print("- GET /api/v1/webhooks/{id}/deliveries - Get endpoint deliveries")
        print("- GET /api/v1/webhooks/events - List event types")
        print("- POST /api/v1/webhooks/events/emit - Emit custom event")
        print("- GET /api/v1/webhooks/stats - Get global statistics")
        print("- GET /api/v1/webhooks/deliveries - Get all deliveries")
        print("- POST /api/v1/webhooks/cleanup - Clean up old deliveries")
        
        # Run the API
        api.run(debug=True)
    
    # Note: In a real application, you would run this differently
    # to properly handle the async webhook system
    print("Starting webhook management API...")
    print("Note: This example requires proper async integration in production")