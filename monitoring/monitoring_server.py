#!/usr/bin/env python3
"""
Monitoring Server
HTTP server providing monitoring endpoints, dashboards, and API access
to the comprehensive monitoring infrastructure.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import os

# Web framework
from aiohttp import web, WSMsgType
from aiohttp.web import Request, Response, WebSocketResponse
import aiohttp_cors

# Monitoring infrastructure
from monitoring_infrastructure import (
    MonitoringInfrastructure, 
    get_monitoring_instance,
    initialize_monitoring,
    shutdown_monitoring,
    AlertSeverity,
    ComponentStatus
)

import structlog

logger = structlog.get_logger(__name__)

class MonitoringServer:
    """HTTP server for monitoring infrastructure"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8090):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.monitoring_infrastructure: Optional[MonitoringInfrastructure] = None
        self.websocket_connections: List[WebSocketResponse] = []
        
        # Setup routes
        self._setup_routes()
        self._setup_cors()
        
        logger.info("Monitoring server initialized", host=host, port=port)
    
    def _setup_routes(self):
        """Setup HTTP routes"""
        # Health and status endpoints
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/status', self.system_status)
        self.app.router.add_get('/metrics', self.prometheus_metrics)
        
        # API endpoints
        self.app.router.add_get('/api/v1/alerts', self.get_alerts)
        self.app.router.add_post('/api/v1/alerts/{alert_id}/resolve', self.resolve_alert)
        self.app.router.add_get('/api/v1/health-checks', self.get_health_checks)
        self.app.router.add_get('/api/v1/system-metrics', self.get_system_metrics)
        
        # Dashboard endpoints
        self.app.router.add_get('/', self.dashboard_home)
        self.app.router.add_get('/dashboard', self.dashboard_home)
        self.app.router.add_get('/dashboard/alerts', self.dashboard_alerts)
        self.app.router.add_get('/dashboard/metrics', self.dashboard_metrics)
        
        # WebSocket endpoint for real-time updates
        self.app.router.add_get('/ws', self.websocket_handler)
        
        # Static files for dashboard
        self.app.router.add_static('/', path=str(Path(__file__).parent / 'static'), name='static')
    
    def _setup_cors(self):
        """Setup CORS for API access"""
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # Add CORS to all routes
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    async def start(self):
        """Start the monitoring server"""
        # Initialize monitoring infrastructure
        self.monitoring_infrastructure = await initialize_monitoring()
        
        # Start background tasks
        asyncio.create_task(self._websocket_broadcast_loop())
        
        # Create and start the web server
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        logger.info(f"Monitoring server started on http://{self.host}:{self.port}")
    
    async def stop(self):
        """Stop the monitoring server"""
        # Close WebSocket connections
        for ws in self.websocket_connections:
            if not ws.closed:
                await ws.close()
        
        # Shutdown monitoring infrastructure
        await shutdown_monitoring()
        
        logger.info("Monitoring server stopped")
    
    # Health and Status Endpoints
    
    async def health_check(self, request: Request) -> Response:
        """Health check endpoint"""
        try:
            if not self.monitoring_infrastructure:
                return web.json_response({
                    'status': 'unhealthy',
                    'message': 'Monitoring infrastructure not initialized',
                    'timestamp': datetime.now().isoformat()
                }, status=503)
            
            health_status = self.monitoring_infrastructure.get_system_status()
            
            status_code = 200
            if health_status['overall_status'] == ComponentStatus.UNHEALTHY.value:
                status_code = 503
            elif health_status['overall_status'] == ComponentStatus.DEGRADED.value:
                status_code = 200  # Still operational but degraded
            
            return web.json_response({
                'status': 'healthy' if status_code == 200 else 'unhealthy',
                'overall_status': health_status['overall_status'],
                'timestamp': health_status['timestamp'],
                'details': health_status
            }, status=status_code)
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return web.json_response({
                'status': 'unhealthy',
                'message': f'Health check failed: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }, status=503)
    
    async def system_status(self, request: Request) -> Response:
        """Detailed system status endpoint"""
        try:
            if not self.monitoring_infrastructure:
                return web.json_response({
                    'error': 'Monitoring infrastructure not initialized'
                }, status=503)
            
            status = self.monitoring_infrastructure.get_system_status()
            return web.json_response(status)
            
        except Exception as e:
            logger.error(f"System status failed: {e}")
            return web.json_response({
                'error': f'System status failed: {str(e)}'
            }, status=500)
    
    async def prometheus_metrics(self, request: Request) -> Response:
        """Prometheus metrics endpoint"""
        try:
            if not self.monitoring_infrastructure:
                return web.Response(text="# Monitoring infrastructure not initialized\\n", 
                                  content_type='text/plain', status=503)
            
            metrics_text = self.monitoring_infrastructure.get_metrics_endpoint()
            return web.Response(text=metrics_text, content_type='text/plain')
            
        except Exception as e:
            logger.error(f"Metrics endpoint failed: {e}")
            return web.Response(text=f"# Error: {str(e)}\\n", 
                              content_type='text/plain', status=500)
    
    # API Endpoints
    
    async def get_alerts(self, request: Request) -> Response:
        """Get all alerts"""
        try:
            if not self.monitoring_infrastructure:
                return web.json_response({'error': 'Monitoring infrastructure not initialized'}, status=503)
            
            # Get query parameters
            severity = request.query.get('severity')
            component = request.query.get('component')
            resolved = request.query.get('resolved', 'false').lower() == 'true'
            
            alerts = self.monitoring_infrastructure.alert_manager.alerts.values()
            
            # Filter alerts
            filtered_alerts = []
            for alert in alerts:
                if resolved and not alert.resolved:
                    continue
                if not resolved and alert.resolved:
                    continue
                if severity and alert.severity.value != severity.upper():
                    continue
                if component and alert.component != component:
                    continue
                
                filtered_alerts.append({
                    'alert_id': alert.alert_id,
                    'name': alert.name,
                    'severity': alert.severity.value,
                    'message': alert.message,
                    'component': alert.component,
                    'timestamp': alert.timestamp.isoformat(),
                    'resolved': alert.resolved,
                    'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
                    'labels': alert.labels,
                    'metadata': alert.metadata
                })
            
            return web.json_response({
                'alerts': filtered_alerts,
                'total': len(filtered_alerts),
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Get alerts failed: {e}")
            return web.json_response({'error': f'Get alerts failed: {str(e)}'}, status=500)
    
    async def resolve_alert(self, request: Request) -> Response:
        """Resolve an alert"""
        try:
            if not self.monitoring_infrastructure:
                return web.json_response({'error': 'Monitoring infrastructure not initialized'}, status=503)
            
            alert_id = request.match_info['alert_id']
            
            success = await self.monitoring_infrastructure.alert_manager.resolve_alert(alert_id)
            
            if success:
                return web.json_response({
                    'success': True,
                    'message': f'Alert {alert_id} resolved',
                    'timestamp': datetime.now().isoformat()
                })
            else:
                return web.json_response({
                    'success': False,
                    'message': f'Alert {alert_id} not found'
                }, status=404)
                
        except Exception as e:
            logger.error(f"Resolve alert failed: {e}")
            return web.json_response({'error': f'Resolve alert failed: {str(e)}'}, status=500)
    
    async def get_health_checks(self, request: Request) -> Response:
        """Get health check results"""
        try:
            if not self.monitoring_infrastructure:
                return web.json_response({'error': 'Monitoring infrastructure not initialized'}, status=503)
            
            health_checks = await self.monitoring_infrastructure.health_checker.run_health_checks()
            
            results = {}
            for name, check in health_checks.items():
                results[name] = {
                    'status': check.status.value,
                    'message': check.message,
                    'response_time_ms': check.response_time_ms,
                    'timestamp': check.timestamp.isoformat(),
                    'metadata': check.metadata
                }
            
            return web.json_response({
                'health_checks': results,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Get health checks failed: {e}")
            return web.json_response({'error': f'Get health checks failed: {str(e)}'}, status=500)
    
    async def get_system_metrics(self, request: Request) -> Response:
        """Get current system metrics"""
        try:
            if not self.monitoring_infrastructure:
                return web.json_response({'error': 'Monitoring infrastructure not initialized'}, status=503)
            
            metrics = self.monitoring_infrastructure.system_monitor.collect_system_metrics()
            
            return web.json_response({
                'system_metrics': {
                    'cpu_percent': metrics.cpu_percent,
                    'memory_percent': metrics.memory_percent,
                    'memory_used_gb': metrics.memory_used_gb,
                    'memory_total_gb': metrics.memory_total_gb,
                    'disk_percent': metrics.disk_percent,
                    'disk_used_gb': metrics.disk_used_gb,
                    'disk_total_gb': metrics.disk_total_gb,
                    'network_bytes_sent': metrics.network_bytes_sent,
                    'network_bytes_recv': metrics.network_bytes_recv,
                    'load_average': metrics.load_average,
                    'process_count': metrics.process_count,
                    'thread_count': metrics.thread_count,
                    'timestamp': metrics.timestamp.isoformat()
                }
            })
            
        except Exception as e:
            logger.error(f"Get system metrics failed: {e}")
            return web.json_response({'error': f'Get system metrics failed: {str(e)}'}, status=500)
    
    # Dashboard Endpoints
    
    async def dashboard_home(self, request: Request) -> Response:
        """Main dashboard page"""
        html_content = self._generate_dashboard_html()
        return web.Response(text=html_content, content_type='text/html')
    
    async def dashboard_alerts(self, request: Request) -> Response:
        """Alerts dashboard page"""
        html_content = self._generate_alerts_dashboard_html()
        return web.Response(text=html_content, content_type='text/html')
    
    async def dashboard_metrics(self, request: Request) -> Response:
        """Metrics dashboard page"""
        html_content = self._generate_metrics_dashboard_html()
        return web.Response(text=html_content, content_type='text/html')
    
    # WebSocket Handler
    
    async def websocket_handler(self, request: Request) -> WebSocketResponse:
        """WebSocket handler for real-time updates"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websocket_connections.append(ws)
        logger.info("WebSocket connection established")
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._handle_websocket_message(ws, data)
                    except json.JSONDecodeError:
                        await ws.send_str(json.dumps({
                            'error': 'Invalid JSON message'
                        }))
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f'WebSocket error: {ws.exception()}')
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
        finally:
            if ws in self.websocket_connections:
                self.websocket_connections.remove(ws)
            logger.info("WebSocket connection closed")
        
        return ws
    
    async def _handle_websocket_message(self, ws: WebSocketResponse, data: Dict[str, Any]):
        """Handle WebSocket message"""
        message_type = data.get('type')
        
        if message_type == 'subscribe':
            # Send current status
            if self.monitoring_infrastructure:
                status = self.monitoring_infrastructure.get_system_status()
                await ws.send_str(json.dumps({
                    'type': 'status_update',
                    'data': status
                }))
        elif message_type == 'ping':
            await ws.send_str(json.dumps({
                'type': 'pong',
                'timestamp': datetime.now().isoformat()
            }))
    
    async def _websocket_broadcast_loop(self):
        """Background task to broadcast updates to WebSocket clients"""
        while True:
            try:
                if self.websocket_connections and self.monitoring_infrastructure:
                    status = self.monitoring_infrastructure.get_system_status()
                    message = json.dumps({
                        'type': 'status_update',
                        'data': status
                    })
                    
                    # Send to all connected clients
                    disconnected = []
                    for ws in self.websocket_connections:
                        try:
                            if not ws.closed:
                                await ws.send_str(message)
                            else:
                                disconnected.append(ws)
                        except Exception as e:
                            logger.error(f"Error sending WebSocket message: {e}")
                            disconnected.append(ws)
                    
                    # Remove disconnected clients
                    for ws in disconnected:
                        if ws in self.websocket_connections:
                            self.websocket_connections.remove(ws)
                
                await asyncio.sleep(5)  # Broadcast every 5 seconds
                
            except Exception as e:
                logger.error(f"WebSocket broadcast error: {e}")
                await asyncio.sleep(5)
    
    # HTML Generation Methods
    
    def _generate_dashboard_html(self) -> str:
        """Generate main dashboard HTML"""
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trading System Monitoring Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        .header { background-color: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .dashboard-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .status-healthy { color: #27ae60; }
        .status-degraded { color: #f39c12; }
        .status-unhealthy { color: #e74c3c; }
        .metric-value { font-size: 2em; font-weight: bold; }
        .metric-label { color: #7f8c8d; font-size: 0.9em; }
        .nav-links { margin-top: 10px; }
        .nav-links a { color: #3498db; text-decoration: none; margin-right: 15px; }
        .nav-links a:hover { text-decoration: underline; }
        .refresh-btn { background: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
        .refresh-btn:hover { background: #2980b9; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Trading System Monitoring Dashboard</h1>
        <div class="nav-links">
            <a href="/dashboard">Overview</a>
            <a href="/dashboard/alerts">Alerts</a>
            <a href="/dashboard/metrics">Metrics</a>
            <a href="/metrics">Prometheus Metrics</a>
        </div>
    </div>
    
    <div style="margin-bottom: 20px;">
        <button class="refresh-btn" onclick="location.reload()">Refresh Dashboard</button>
        <span id="last-updated" style="margin-left: 20px; color: #7f8c8d;"></span>
    </div>
    
    <div class="dashboard-grid">
        <div class="card">
            <h3>System Status</h3>
            <div id="system-status">Loading...</div>
        </div>
        
        <div class="card">
            <h3>Active Alerts</h3>
            <div id="active-alerts">Loading...</div>
        </div>
        
        <div class="card">
            <h3>System Metrics</h3>
            <div id="system-metrics">Loading...</div>
        </div>
        
        <div class="card">
            <h3>Health Checks</h3>
            <div id="health-checks">Loading...</div>
        </div>
    </div>
    
    <script>
        let ws = null;
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
            
            ws.onopen = function() {
                console.log('WebSocket connected');
                ws.send(JSON.stringify({type: 'subscribe'}));
            };
            
            ws.onmessage = function(event) {
                const message = JSON.parse(event.data);
                if (message.type === 'status_update') {
                    updateDashboard(message.data);
                }
            };
            
            ws.onclose = function() {
                console.log('WebSocket disconnected, reconnecting...');
                setTimeout(connectWebSocket, 5000);
            };
        }
        
        function updateDashboard(data) {
            // Update system status
            const statusElement = document.getElementById('system-status');
            const statusClass = `status-${data.overall_status.toLowerCase()}`;
            statusElement.innerHTML = `<span class="${statusClass}">${data.overall_status}</span>`;
            
            // Update active alerts
            const alertsElement = document.getElementById('active-alerts');
            const alertCount = data.alerts.active_count;
            alertsElement.innerHTML = `
                <div class="metric-value">${alertCount}</div>
                <div class="metric-label">Active Alerts</div>
            `;
            
            // Update system metrics (placeholder)
            const metricsElement = document.getElementById('system-metrics');
            metricsElement.innerHTML = `
                <div>Monitoring: ${data.metrics.system_monitoring ? 'Active' : 'Inactive'}</div>
                <div class="metric-label">Collection Enabled: ${data.metrics.collection_enabled}</div>
            `;
            
            // Update health checks
            const healthElement = document.getElementById('health-checks');
            const healthChecks = Object.entries(data.health_checks);
            const healthHtml = healthChecks.map(([name, check]) => 
                `<div><strong>${name}:</strong> <span class="status-${check.status.toLowerCase()}">${check.status}</span></div>`
            ).join('');
            healthElement.innerHTML = healthHtml || 'No health checks available';
            
            // Update timestamp
            document.getElementById('last-updated').textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
        }
        
        // Initialize WebSocket connection
        connectWebSocket();
        
        // Fallback: refresh every 30 seconds if WebSocket fails
        setInterval(() => {
            if (!ws || ws.readyState !== WebSocket.OPEN) {
                location.reload();
            }
        }, 30000);
    </script>
</body>
</html>
        '''
    
    def _generate_alerts_dashboard_html(self) -> str:
        """Generate alerts dashboard HTML"""
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Alerts Dashboard - Trading System Monitoring</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        .header { background-color: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .nav-links a { color: #3498db; text-decoration: none; margin-right: 15px; }
        .nav-links a:hover { text-decoration: underline; }
        .alerts-container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .alert-item { border-left: 4px solid #ccc; padding: 15px; margin-bottom: 10px; background: #f9f9f9; }
        .alert-critical { border-left-color: #e74c3c; }
        .alert-warning { border-left-color: #f39c12; }
        .alert-info { border-left-color: #3498db; }
        .alert-header { font-weight: bold; margin-bottom: 5px; }
        .alert-meta { color: #7f8c8d; font-size: 0.9em; }
        .resolve-btn { background: #27ae60; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; }
        .resolve-btn:hover { background: #229954; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Alerts Dashboard</h1>
        <div class="nav-links">
            <a href="/dashboard">Overview</a>
            <a href="/dashboard/alerts">Alerts</a>
            <a href="/dashboard/metrics">Metrics</a>
            <a href="/metrics">Prometheus Metrics</a>
        </div>
    </div>
    
    <div class="alerts-container">
        <h2>Active Alerts</h2>
        <div id="alerts-list">Loading alerts...</div>
    </div>
    
    <script>
        async function loadAlerts() {
            try {
                const response = await fetch('/api/v1/alerts');
                const data = await response.json();
                
                const alertsList = document.getElementById('alerts-list');
                
                if (data.alerts.length === 0) {
                    alertsList.innerHTML = '<p>No active alerts</p>';
                    return;
                }
                
                const alertsHtml = data.alerts.map(alert => `
                    <div class="alert-item alert-${alert.severity.toLowerCase()}">
                        <div class="alert-header">${alert.name}</div>
                        <div>${alert.message}</div>
                        <div class="alert-meta">
                            Component: ${alert.component} | 
                            Severity: ${alert.severity} | 
                            Time: ${new Date(alert.timestamp).toLocaleString()}
                            ${!alert.resolved ? `<button class="resolve-btn" onclick="resolveAlert('${alert.alert_id}')">Resolve</button>` : ''}
                        </div>
                    </div>
                `).join('');
                
                alertsList.innerHTML = alertsHtml;
            } catch (error) {
                console.error('Failed to load alerts:', error);
                document.getElementById('alerts-list').innerHTML = '<p>Failed to load alerts</p>';
            }
        }
        
        async function resolveAlert(alertId) {
            try {
                const response = await fetch(`/api/v1/alerts/${alertId}/resolve`, {
                    method: 'POST'
                });
                
                if (response.ok) {
                    loadAlerts(); // Reload alerts
                } else {
                    alert('Failed to resolve alert');
                }
            } catch (error) {
                console.error('Failed to resolve alert:', error);
                alert('Failed to resolve alert');
            }
        }
        
        // Load alerts on page load
        loadAlerts();
        
        // Refresh alerts every 30 seconds
        setInterval(loadAlerts, 30000);
    </script>
</body>
</html>
        '''
    
    def _generate_metrics_dashboard_html(self) -> str:
        """Generate metrics dashboard HTML"""
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Metrics Dashboard - Trading System Monitoring</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        .header { background-color: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .nav-links a { color: #3498db; text-decoration: none; margin-right: 15px; }
        .nav-links a:hover { text-decoration: underline; }
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }
        .metric-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric-value { font-size: 2.5em; font-weight: bold; color: #2c3e50; }
        .metric-label { color: #7f8c8d; font-size: 1.1em; margin-bottom: 10px; }
        .metric-unit { font-size: 0.8em; color: #95a5a6; }
        .progress-bar { width: 100%; height: 20px; background: #ecf0f1; border-radius: 10px; overflow: hidden; margin-top: 10px; }
        .progress-fill { height: 100%; background: #3498db; transition: width 0.3s ease; }
        .progress-warning { background: #f39c12; }
        .progress-danger { background: #e74c3c; }
    </style>
</head>
<body>
    <div class="header">
        <h1>System Metrics Dashboard</h1>
        <div class="nav-links">
            <a href="/dashboard">Overview</a>
            <a href="/dashboard/alerts">Alerts</a>
            <a href="/dashboard/metrics">Metrics</a>
            <a href="/metrics">Prometheus Metrics</a>
        </div>
    </div>
    
    <div class="metrics-grid" id="metrics-grid">
        Loading metrics...
    </div>
    
    <script>
        async function loadMetrics() {
            try {
                const response = await fetch('/api/v1/system-metrics');
                const data = await response.json();
                const metrics = data.system_metrics;
                
                const metricsGrid = document.getElementById('metrics-grid');
                
                const metricsHtml = `
                    <div class="metric-card">
                        <div class="metric-label">CPU Usage</div>
                        <div class="metric-value">${metrics.cpu_percent.toFixed(1)}<span class="metric-unit">%</span></div>
                        <div class="progress-bar">
                            <div class="progress-fill ${getProgressClass(metrics.cpu_percent)}" style="width: ${metrics.cpu_percent}%"></div>
                        </div>
                    </div>
                    
                    <div class="metric-card">
                        <div class="metric-label">Memory Usage</div>
                        <div class="metric-value">${metrics.memory_percent.toFixed(1)}<span class="metric-unit">%</span></div>
                        <div class="progress-bar">
                            <div class="progress-fill ${getProgressClass(metrics.memory_percent)}" style="width: ${metrics.memory_percent}%"></div>
                        </div>
                        <div style="margin-top: 5px; font-size: 0.9em; color: #7f8c8d;">
                            ${metrics.memory_used_gb.toFixed(1)} GB / ${metrics.memory_total_gb.toFixed(1)} GB
                        </div>
                    </div>
                    
                    <div class="metric-card">
                        <div class="metric-label">Disk Usage</div>
                        <div class="metric-value">${metrics.disk_percent.toFixed(1)}<span class="metric-unit">%</span></div>
                        <div class="progress-bar">
                            <div class="progress-fill ${getProgressClass(metrics.disk_percent)}" style="width: ${metrics.disk_percent}%"></div>
                        </div>
                        <div style="margin-top: 5px; font-size: 0.9em; color: #7f8c8d;">
                            ${metrics.disk_used_gb.toFixed(1)} GB / ${metrics.disk_total_gb.toFixed(1)} GB
                        </div>
                    </div>
                    
                    <div class="metric-card">
                        <div class="metric-label">Load Average</div>
                        <div class="metric-value">${metrics.load_average[0].toFixed(2)}</div>
                        <div style="font-size: 0.9em; color: #7f8c8d;">
                            1m: ${metrics.load_average[0].toFixed(2)} | 
                            5m: ${metrics.load_average[1].toFixed(2)} | 
                            15m: ${metrics.load_average[2].toFixed(2)}
                        </div>
                    </div>
                    
                    <div class="metric-card">
                        <div class="metric-label">Processes</div>
                        <div class="metric-value">${metrics.process_count}</div>
                        <div style="font-size: 0.9em; color: #7f8c8d;">
                            Threads: ${metrics.thread_count}
                        </div>
                    </div>
                    
                    <div class="metric-card">
                        <div class="metric-label">Network I/O</div>
                        <div style="font-size: 0.9em;">
                            <div>Sent: ${formatBytes(metrics.network_bytes_sent)}</div>
                            <div>Received: ${formatBytes(metrics.network_bytes_recv)}</div>
                        </div>
                    </div>
                `;
                
                metricsGrid.innerHTML = metricsHtml;
                
            } catch (error) {
                console.error('Failed to load metrics:', error);
                document.getElementById('metrics-grid').innerHTML = '<p>Failed to load metrics</p>';
            }
        }
        
        function getProgressClass(value) {
            if (value > 80) return 'progress-danger';
            if (value > 60) return 'progress-warning';
            return '';
        }
        
        function formatBytes(bytes) {
            const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
            if (bytes === 0) return '0 Bytes';
            const i = Math.floor(Math.log(bytes) / Math.log(1024));
            return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
        }
        
        // Load metrics on page load
        loadMetrics();
        
        // Refresh metrics every 10 seconds
        setInterval(loadMetrics, 10000);
    </script>
</body>
</html>
        '''

async def main():
    """Main function to run the monitoring server"""
    server = MonitoringServer(host="0.0.0.0", port=8090)
    
    try:
        await server.start()
        
        logger.info("Monitoring server is running. Press Ctrl+C to stop.")
        
        # Keep the server running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down monitoring server...")
    finally:
        await server.stop()

if __name__ == "__main__":
    asyncio.run(main())