"""
Dashboard Frontend Components
Provides HTML templates and JavaScript components for the dashboard builder,
including drag-and-drop functionality, real-time collaboration, and responsive design.
"""
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json

class DashboardFrontend:
    """Dashboard frontend template and component generator"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_dashboard_builder_html(self) -> str:
        """Generate dashboard builder HTML template"""
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Builder - Nautilus Trader</title>
    
    <!-- CSS Dependencies -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/gridstack@8.4.0/dist/gridstack.min.css" rel="stylesheet">
    
    <style>
        /* Dashboard Builder Styles */
        .dashboard-builder {
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        .builder-header {
            background: #2c3e50;
            color: white;
            padding: 1rem;
            display: flex;
            justify-content: between;
            align-items: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .builder-toolbar {
            background: #34495e;
            color: white;
            padding: 0.5rem 1rem;
            display: flex;
            gap: 1rem;
            align-items: center;
            border-bottom: 1px solid #2c3e50;
        }
        
        .builder-content {
            flex: 1;
            display: flex;
            overflow: hidden;
        }
        
        .widget-palette {
            width: 300px;
            background: #f8f9fa;
            border-right: 1px solid #dee2e6;
            overflow-y: auto;
            padding: 1rem;
        }
        
        .dashboard-canvas {
            flex: 1;
            background: #ffffff;
            position: relative;
            overflow: auto;
        }
        
        .properties-panel {
            width: 300px;
            background: #f8f9fa;
            border-left: 1px solid #dee2e6;
            overflow-y: auto;
            padding: 1rem;
        }
        
        /* Widget Palette Styles */
        .widget-category {
            margin-bottom: 1.5rem;
        }
        
        .widget-category h6 {
            color: #495057;
            font-weight: 600;
            margin-bottom: 0.5rem;
            padding-bottom: 0.25rem;
            border-bottom: 1px solid #dee2e6;
        }
        
        .widget-template {
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 0.375rem;
            padding: 0.75rem;
            margin-bottom: 0.5rem;
            cursor: grab;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .widget-template:hover {
            border-color: #007bff;
            box-shadow: 0 2px 4px rgba(0,123,255,0.15);
            transform: translateY(-1px);
        }
        
        .widget-template:active {
            cursor: grabbing;
        }
        
        .widget-template-icon {
            width: 32px;
            height: 32px;
            background: #e9ecef;
            border-radius: 0.25rem;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #6c757d;
        }
        
        .widget-template-info h6 {
            margin: 0;
            font-size: 0.875rem;
            font-weight: 600;
            color: #212529;
        }
        
        .widget-template-info p {
            margin: 0;
            font-size: 0.75rem;
            color: #6c757d;
        }
        
        /* GridStack Customization */
        .grid-stack {
            background: #f8f9fa;
            min-height: 100vh;
            padding: 1rem;
        }
        
        .grid-stack-item {
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 0.375rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            transition: all 0.2s ease;
        }
        
        .grid-stack-item:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        .grid-stack-item.selected {
            border-color: #007bff;
            box-shadow: 0 0 0 2px rgba(0,123,255,0.25);
        }
        
        .grid-stack-item-content {
            height: 100%;
            padding: 1rem;
            display: flex;
            flex-direction: column;
        }
        
        .widget-header {
            display: flex;
            justify-content: between;
            align-items: center;
            margin-bottom: 0.5rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #e9ecef;
        }
        
        .widget-title {
            font-weight: 600;
            color: #212529;
            margin: 0;
            font-size: 0.875rem;
        }
        
        .widget-actions {
            display: flex;
            gap: 0.25rem;
        }
        
        .widget-action {
            background: none;
            border: none;
            color: #6c757d;
            cursor: pointer;
            padding: 0.25rem;
            border-radius: 0.25rem;
            transition: all 0.2s ease;
        }
        
        .widget-action:hover {
            background: #e9ecef;
            color: #495057;
        }
        
        .widget-content {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #6c757d;
            font-size: 0.875rem;
        }
        
        /* Properties Panel Styles */
        .properties-section {
            margin-bottom: 1.5rem;
        }
        
        .properties-section h6 {
            color: #495057;
            font-weight: 600;
            margin-bottom: 0.75rem;
            padding-bottom: 0.25rem;
            border-bottom: 1px solid #dee2e6;
        }
        
        .form-group {
            margin-bottom: 1rem;
        }
        
        .form-label {
            font-size: 0.875rem;
            font-weight: 500;
            color: #495057;
            margin-bottom: 0.25rem;
        }
        
        .form-control {
            font-size: 0.875rem;
        }
        
        /* Collaboration Indicators */
        .collaboration-bar {
            background: #e3f2fd;
            border-bottom: 1px solid #bbdefb;
            padding: 0.5rem 1rem;
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        
        .active-users {
            display: flex;
            gap: 0.5rem;
            align-items: center;
        }
        
        .user-avatar {
            width: 24px;
            height: 24px;
            border-radius: 50%;
            background: #007bff;
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.75rem;
            font-weight: 600;
        }
        
        .user-cursor {
            position: absolute;
            pointer-events: none;
            z-index: 1000;
            transition: all 0.1s ease;
        }
        
        .cursor-pointer {
            width: 0;
            height: 0;
            border-left: 8px solid;
            border-top: 8px solid transparent;
            border-bottom: 8px solid transparent;
        }
        
        .cursor-label {
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.75rem;
            margin-left: 12px;
            margin-top: -4px;
        }
        
        /* Responsive Design */
        @media (max-width: 1200px) {
            .widget-palette,
            .properties-panel {
                width: 250px;
            }
        }
        
        @media (max-width: 992px) {
            .builder-content {
                flex-direction: column;
            }
            
            .widget-palette,
            .properties-panel {
                width: 100%;
                height: 200px;
            }
        }
        
        /* Dark Theme */
        .dark-theme {
            background: #1a1a1a;
            color: #e0e0e0;
        }
        
        .dark-theme .builder-header {
            background: #2d2d2d;
        }
        
        .dark-theme .builder-toolbar {
            background: #3d3d3d;
        }
        
        .dark-theme .widget-palette,
        .dark-theme .properties-panel {
            background: #2d2d2d;
            border-color: #404040;
        }
        
        .dark-theme .dashboard-canvas {
            background: #1a1a1a;
        }
        
        .dark-theme .grid-stack {
            background: #1a1a1a;
        }
        
        .dark-theme .grid-stack-item {
            background: #2d2d2d;
            border-color: #404040;
        }
        
        .dark-theme .widget-template {
            background: #2d2d2d;
            border-color: #404040;
        }
    </style>
</head>
<body>
    <div class="dashboard-builder">
        <!-- Header -->
        <div class="builder-header">
            <div class="d-flex align-items-center">
                <h4 class="mb-0">
                    <i class="fas fa-chart-line me-2"></i>
                    Dashboard Builder
                </h4>
                <span class="badge bg-secondary ms-2" id="dashboard-name">Untitled Dashboard</span>
            </div>
            
            <div class="d-flex align-items-center gap-2">
                <button class="btn btn-outline-light btn-sm" id="preview-btn">
                    <i class="fas fa-eye"></i> Preview
                </button>
                <button class="btn btn-outline-light btn-sm" id="share-btn">
                    <i class="fas fa-share"></i> Share
                </button>
                <button class="btn btn-success btn-sm" id="save-btn">
                    <i class="fas fa-save"></i> Save
                </button>
            </div>
        </div>
        
        <!-- Toolbar -->
        <div class="builder-toolbar">
            <button class="btn btn-sm btn-outline-light" id="undo-btn">
                <i class="fas fa-undo"></i>
            </button>
            <button class="btn btn-sm btn-outline-light" id="redo-btn">
                <i class="fas fa-redo"></i>
            </button>
            
            <div class="vr"></div>
            
            <div class="form-check form-switch">
                <input class="form-check-input" type="checkbox" id="grid-snap" checked>
                <label class="form-check-label" for="grid-snap">Grid Snap</label>
            </div>
            
            <div class="form-check form-switch">
                <input class="form-check-input" type="checkbox" id="show-grid">
                <label class="form-check-label" for="show-grid">Show Grid</label>
            </div>
            
            <div class="vr"></div>
            
            <select class="form-select form-select-sm" id="theme-select" style="width: auto;">
                <option value="light">Light Theme</option>
                <option value="dark">Dark Theme</option>
                <option value="blue">Blue Theme</option>
            </select>
        </div>
        
        <!-- Collaboration Bar -->
        <div class="collaboration-bar" id="collaboration-bar" style="display: none;">
            <div class="active-users">
                <span class="text-muted">Active users:</span>
                <div id="active-users-list"></div>
            </div>
            <div class="ms-auto">
                <span class="badge bg-success">
                    <i class="fas fa-circle"></i> Live
                </span>
            </div>
        </div>
        
        <!-- Main Content -->
        <div class="builder-content">
            <!-- Widget Palette -->
            <div class="widget-palette">
                <h5 class="mb-3">
                    <i class="fas fa-puzzle-piece me-2"></i>
                    Widgets
                </h5>
                
                <div class="widget-category">
                    <h6>Trading</h6>
                    <div class="widget-template" data-template="portfolio_summary">
                        <div class="widget-template-icon">
                            <i class="fas fa-chart-pie"></i>
                        </div>
                        <div class="widget-template-info">
                            <h6>Portfolio Summary</h6>
                            <p>Portfolio value and performance</p>
                        </div>
                    </div>
                    
                    <div class="widget-template" data-template="positions_table">
                        <div class="widget-template-icon">
                            <i class="fas fa-table"></i>
                        </div>
                        <div class="widget-template-info">
                            <h6>Positions Table</h6>
                            <p>Detailed positions view</p>
                        </div>
                    </div>
                </div>
                
                <div class="widget-category">
                    <h6>Analytics</h6>
                    <div class="widget-template" data-template="pnl_chart">
                        <div class="widget-template-icon">
                            <i class="fas fa-chart-line"></i>
                        </div>
                        <div class="widget-template-info">
                            <h6>P&L Chart</h6>
                            <p>Profit and loss over time</p>
                        </div>
                    </div>
                    
                    <div class="widget-template" data-template="performance_metrics">
                        <div class="widget-template-icon">
                            <i class="fas fa-tachometer-alt"></i>
                        </div>
                        <div class="widget-template-info">
                            <h6>Performance Metrics</h6>
                            <p>Key performance indicators</p>
                        </div>
                    </div>
                </div>
                
                <div class="widget-category">
                    <h6>Market Data</h6>
                    <div class="widget-template" data-template="watchlist">
                        <div class="widget-template-icon">
                            <i class="fas fa-list"></i>
                        </div>
                        <div class="widget-template-info">
                            <h6>Watchlist</h6>
                            <p>Market watchlist with prices</p>
                        </div>
                    </div>
                    
                    <div class="widget-template" data-template="order_book">
                        <div class="widget-template-icon">
                            <i class="fas fa-book"></i>
                        </div>
                        <div class="widget-template-info">
                            <h6>Order Book</h6>
                            <p>Real-time order book data</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Dashboard Canvas -->
            <div class="dashboard-canvas">
                <div class="grid-stack" id="dashboard-grid"></div>
            </div>
            
            <!-- Properties Panel -->
            <div class="properties-panel">
                <h5 class="mb-3">
                    <i class="fas fa-cog me-2"></i>
                    Properties
                </h5>
                
                <div id="widget-properties" style="display: none;">
                    <div class="properties-section">
                        <h6>Widget Settings</h6>
                        
                        <div class="form-group">
                            <label class="form-label">Title</label>
                            <input type="text" class="form-control" id="widget-title">
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">Data Source</label>
                            <select class="form-select" id="widget-data-source">
                                <option value="">Select data source...</option>
                                <option value="portfolio_value">Portfolio Value</option>
                                <option value="positions">Positions</option>
                                <option value="orders">Orders</option>
                                <option value="pnl_chart">P&L Chart</option>
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">Refresh Interval (seconds)</label>
                            <input type="number" class="form-control" id="widget-refresh" min="5" max="300" value="30">
                        </div>
                    </div>
                    
                    <div class="properties-section">
                        <h6>Appearance</h6>
                        
                        <div class="form-group">
                            <label class="form-label">Background Color</label>
                            <input type="color" class="form-control form-control-color" id="widget-bg-color" value="#ffffff">
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">Border Color</label>
                            <input type="color" class="form-control form-control-color" id="widget-border-color" value="#dee2e6">
                        </div>
                        
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="widget-shadow">
                            <label class="form-check-label" for="widget-shadow">
                                Drop Shadow
                            </label>
                        </div>
                    </div>
                    
                    <div class="properties-section">
                        <h6>Actions</h6>
                        
                        <button class="btn btn-outline-primary btn-sm w-100 mb-2" id="duplicate-widget">
                            <i class="fas fa-copy"></i> Duplicate
                        </button>
                        
                        <button class="btn btn-outline-danger btn-sm w-100" id="delete-widget">
                            <i class="fas fa-trash"></i> Delete
                        </button>
                    </div>
                </div>
                
                <div id="dashboard-properties">
                    <div class="properties-section">
                        <h6>Dashboard Settings</h6>
                        
                        <div class="form-group">
                            <label class="form-label">Name</label>
                            <input type="text" class="form-control" id="dashboard-title" placeholder="Dashboard Name">
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">Description</label>
                            <textarea class="form-control" id="dashboard-description" rows="3" placeholder="Dashboard description..."></textarea>
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">Tags</label>
                            <input type="text" class="form-control" id="dashboard-tags" placeholder="trading, analytics, risk">
                        </div>
                    </div>
                    
                    <div class="properties-section">
                        <h6>Layout</h6>
                        
                        <div class="form-group">
                            <label class="form-label">Grid Columns</label>
                            <input type="number" class="form-control" id="grid-columns" min="6" max="24" value="12">
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">Row Height (px)</label>
                            <input type="number" class="form-control" id="row-height" min="30" max="100" value="60">
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">Margin</label>
                            <input type="number" class="form-control" id="grid-margin" min="0" max="20" value="10">
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Modals -->
    <div class="modal fade" id="shareModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Share Dashboard</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="form-group mb-3">
                        <label class="form-label">Share Type</label>
                        <select class="form-select" id="share-type">
                            <option value="public">Public - Anyone with link</option>
                            <option value="private">Private - Specific users only</option>
                            <option value="team">Team - Team members only</option>
                        </select>
                    </div>
                    
                    <div class="form-group mb-3">
                        <label class="form-label">Permission Level</label>
                        <select class="form-select" id="permission-level">
                            <option value="view">View Only</option>
                            <option value="comment">View & Comment</option>
                            <option value="edit">Edit</option>
                        </select>
                    </div>
                    
                    <div class="form-group mb-3">
                        <label class="form-label">Expiration</label>
                        <select class="form-select" id="share-expiration">
                            <option value="">Never</option>
                            <option value="24">24 hours</option>
                            <option value="168">1 week</option>
                            <option value="720">1 month</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Share Link</label>
                        <div class="input-group">
                            <input type="text" class="form-control" id="share-link" readonly>
                            <button class="btn btn-outline-secondary" type="button" id="copy-link">
                                <i class="fas fa-copy"></i>
                            </button>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    <button type="button" class="btn btn-primary" id="create-share">Create Share Link</button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- JavaScript Dependencies -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/gridstack@8.4.0/dist/gridstack-all.js"></script>
    <script src="https://cdn.socket.io/4.5.0/socket.io.min.js"></script>
    
    <script>
        // Dashboard Builder JavaScript
        class DashboardBuilder {
            constructor() {
                this.grid = null;
                this.selectedWidget = null;
                this.socket = io();
                this.dashboardId = this.getDashboardId();
                this.collaborativeUsers = new Map();
                
                this.init();
            }
            
            init() {
                this.initGrid();
                this.initEventListeners();
                this.initSocketEvents();
                this.initDragAndDrop();
                
                if (this.dashboardId) {
                    this.loadDashboard();
                    this.joinCollaborativeSession();
                }
            }
            
            getDashboardId() {
                const urlParams = new URLSearchParams(window.location.search);
                return urlParams.get('id') || null;
            }
            
            initGrid() {
                this.grid = GridStack.init({
                    cellHeight: 60,
                    margin: 10,
                    resizable: {
                        handles: 'e, se, s, sw, w'
                    },
                    draggable: {
                        handle: '.widget-header'
                    }
                });
                
                // Grid events
                this.grid.on('change', (event, items) => {
                    this.onGridChange(items);
                });
                
                this.grid.on('added', (event, items) => {
                    this.onWidgetAdded(items);
                });
                
                this.grid.on('removed', (event, items) => {
                    this.onWidgetRemoved(items);
                });
            }
            
            initEventListeners() {
                // Toolbar events
                document.getElementById('save-btn').addEventListener('click', () => this.saveDashboard());
                document.getElementById('preview-btn').addEventListener('click', () => this.previewDashboard());
                document.getElementById('share-btn').addEventListener('click', () => this.showShareModal());
                
                // Grid settings
                document.getElementById('grid-snap').addEventListener('change', (e) => {
                    this.grid.float(!e.target.checked);
                });
                
                document.getElementById('show-grid').addEventListener('change', (e) => {
                    document.querySelector('.grid-stack').classList.toggle('show-grid', e.target.checked);
                });
                
                // Theme selection
                document.getElementById('theme-select').addEventListener('change', (e) => {
                    this.changeTheme(e.target.value);
                });
                
                // Properties panel events
                document.getElementById('widget-title').addEventListener('input', (e) => {
                    this.updateWidgetProperty('title', e.target.value);
                });
                
                document.getElementById('duplicate-widget').addEventListener('click', () => {
                    this.duplicateWidget();
                });
                
                document.getElementById('delete-widget').addEventListener('click', () => {
                    this.deleteWidget();
                });
                
                // Dashboard click to deselect widgets
                document.querySelector('.dashboard-canvas').addEventListener('click', (e) => {
                    if (e.target.classList.contains('dashboard-canvas') || e.target.classList.contains('grid-stack')) {
                        this.selectWidget(null);
                    }
                });
            }
            
            initSocketEvents() {
                this.socket.on('connect', () => {
                    console.log('Connected to dashboard builder');
                });
                
                this.socket.on('widget_drag_started', (data) => {
                    this.showUserCursor(data.user_id, 'dragging');
                });
                
                this.socket.on('widget_drag_ended', (data) => {
                    this.updateWidgetPosition(data.widget_id, data.position);
                });
                
                this.socket.on('collaborative_edit_update', (data) => {
                    this.handleCollaborativeEdit(data);
                });
                
                this.socket.on('user_joined_builder', (data) => {
                    this.addCollaborativeUser(data.user_id, data.username);
                });
                
                this.socket.on('user_left_builder', (data) => {
                    this.removeCollaborativeUser(data.user_id);
                });
            }
            
            initDragAndDrop() {
                const templates = document.querySelectorAll('.widget-template');
                
                templates.forEach(template => {
                    template.addEventListener('dragstart', (e) => {
                        e.dataTransfer.setData('text/plain', template.dataset.template);
                    });
                    
                    template.draggable = true;
                });
                
                // Grid drop handling
                const gridElement = document.getElementById('dashboard-grid');
                
                gridElement.addEventListener('dragover', (e) => {
                    e.preventDefault();
                });
                
                gridElement.addEventListener('drop', (e) => {
                    e.preventDefault();
                    const templateId = e.dataTransfer.getData('text/plain');
                    
                    if (templateId) {
                        const rect = gridElement.getBoundingClientRect();
                        const x = Math.floor((e.clientX - rect.left) / 100); // Approximate grid position
                        const y = Math.floor((e.clientY - rect.top) / 70);
                        
                        this.addWidgetFromTemplate(templateId, { x, y });
                    }
                });
            }
            
            addWidgetFromTemplate(templateId, position = { x: 0, y: 0 }) {
                const widgetId = 'widget_' + Date.now();
                
                // Create widget HTML
                const widgetHtml = `
                    <div class="grid-stack-item-content">
                        <div class="widget-header">
                            <h6 class="widget-title">${this.getTemplateName(templateId)}</h6>
                            <div class="widget-actions">
                                <button class="widget-action" onclick="builder.configureWidget('${widgetId}')">
                                    <i class="fas fa-cog"></i>
                                </button>
                                <button class="widget-action" onclick="builder.deleteWidget('${widgetId}')">
                                    <i class="fas fa-times"></i>
                                </button>
                            </div>
                        </div>
                        <div class="widget-content">
                            <div class="text-muted">
                                <i class="fas fa-chart-line fa-2x mb-2"></i>
                                <div>Widget Content</div>
                            </div>
                        </div>
                    </div>
                `;
                
                // Add to grid
                this.grid.addWidget({
                    id: widgetId,
                    x: position.x,
                    y: position.y,
                    w: 4,
                    h: 3,
                    content: widgetHtml
                });
                
                // Add click handler for selection
                const widgetElement = document.getElementById(widgetId);
                widgetElement.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.selectWidget(widgetId);
                });
                
                // Emit to collaborative session
                if (this.dashboardId) {
                    this.socket.emit('collaborative_edit', {
                        dashboard_id: this.dashboardId,
                        edit_type: 'widget_added',
                        edit_data: {
                            widget_id: widgetId,
                            template_id: templateId,
                            position: position
                        },
                        user_id: this.getCurrentUserId()
                    });
                }
            }
            
            selectWidget(widgetId) {
                // Remove previous selection
                document.querySelectorAll('.grid-stack-item.selected').forEach(item => {
                    item.classList.remove('selected');
                });
                
                this.selectedWidget = widgetId;
                
                if (widgetId) {
                    // Add selection to widget
                    document.getElementById(widgetId).classList.add('selected');
                    
                    // Show widget properties
                    document.getElementById('widget-properties').style.display = 'block';
                    document.getElementById('dashboard-properties').style.display = 'none';
                    
                    // Load widget properties
                    this.loadWidgetProperties(widgetId);
                } else {
                    // Show dashboard properties
                    document.getElementById('widget-properties').style.display = 'none';
                    document.getElementById('dashboard-properties').style.display = 'block';
                }
            }
            
            loadWidgetProperties(widgetId) {
                const widget = document.getElementById(widgetId);
                const title = widget.querySelector('.widget-title').textContent;
                
                document.getElementById('widget-title').value = title;
                // Load other properties...
            }
            
            updateWidgetProperty(property, value) {
                if (!this.selectedWidget) return;
                
                const widget = document.getElementById(this.selectedWidget);
                
                switch (property) {
                    case 'title':
                        widget.querySelector('.widget-title').textContent = value;
                        break;
                    // Handle other properties...
                }
                
                // Emit change to collaborative session
                if (this.dashboardId) {
                    this.socket.emit('collaborative_edit', {
                        dashboard_id: this.dashboardId,
                        edit_type: 'widget_updated',
                        edit_data: {
                            widget_id: this.selectedWidget,
                            property: property,
                            value: value
                        },
                        user_id: this.getCurrentUserId()
                    });
                }
            }
            
            duplicateWidget() {
                if (!this.selectedWidget) return;
                
                const originalWidget = document.getElementById(this.selectedWidget);
                const gridItem = this.grid.getGridItems().find(item => item.gridstackNode.id === this.selectedWidget);
                
                if (gridItem) {
                    const node = gridItem.gridstackNode;
                    this.addWidgetFromTemplate('duplicate', {
                        x: node.x + 1,
                        y: node.y + 1
                    });
                }
            }
            
            deleteWidget(widgetId = null) {
                const targetWidget = widgetId || this.selectedWidget;
                if (!targetWidget) return;
                
                if (confirm('Are you sure you want to delete this widget?')) {
                    this.grid.removeWidget(targetWidget);
                    
                    if (targetWidget === this.selectedWidget) {
                        this.selectWidget(null);
                    }
                    
                    // Emit to collaborative session
                    if (this.dashboardId) {
                        this.socket.emit('collaborative_edit', {
                            dashboard_id: this.dashboardId,
                            edit_type: 'widget_deleted',
                            edit_data: {
                                widget_id: targetWidget
                            },
                            user_id: this.getCurrentUserId()
                        });
                    }
                }
            }
            
            saveDashboard() {
                const dashboardData = this.serializeDashboard();
                
                // Save via API
                fetch('/api/dashboards', {
                    method: this.dashboardId ? 'PUT' : 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(dashboardData)
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        this.showNotification('Dashboard saved successfully', 'success');
                        if (!this.dashboardId) {
                            this.dashboardId = data.dashboard_id;
                            this.updateUrl();
                        }
                    } else {
                        this.showNotification('Failed to save dashboard: ' + data.error, 'error');
                    }
                })
                .catch(error => {
                    this.showNotification('Error saving dashboard: ' + error.message, 'error');
                });
            }
            
            serializeDashboard() {
                const widgets = [];
                
                this.grid.getGridItems().forEach(item => {
                    const node = item.gridstackNode;
                    const widgetElement = item;
                    const title = widgetElement.querySelector('.widget-title').textContent;
                    
                    widgets.push({
                        widget_id: node.id,
                        title: title,
                        position: {
                            x: node.x,
                            y: node.y,
                            w: node.w,
                            h: node.h
                        }
                    });
                });
                
                return {
                    dashboard_id: this.dashboardId,
                    name: document.getElementById('dashboard-title').value || 'Untitled Dashboard',
                    description: document.getElementById('dashboard-description').value || '',
                    widgets: widgets,
                    layout: {
                        grid_columns: parseInt(document.getElementById('grid-columns').value),
                        row_height: parseInt(document.getElementById('row-height').value),
                        margin: parseInt(document.getElementById('grid-margin').value)
                    }
                };
            }
            
            joinCollaborativeSession() {
                this.socket.emit('join_builder', {
                    dashboard_id: this.dashboardId,
                    user_id: this.getCurrentUserId()
                });
            }
            
            getCurrentUserId() {
                // In a real implementation, get from authentication
                return 'user_' + Math.random().toString(36).substr(2, 9);
            }
            
            getTemplateName(templateId) {
                const templateNames = {
                    'portfolio_summary': 'Portfolio Summary',
                    'positions_table': 'Positions Table',
                    'pnl_chart': 'P&L Chart',
                    'performance_metrics': 'Performance Metrics',
                    'watchlist': 'Watchlist',
                    'order_book': 'Order Book'
                };
                
                return templateNames[templateId] || 'Widget';
            }
            
            showNotification(message, type = 'info') {
                // Simple notification implementation
                const notification = document.createElement('div');
                notification.className = `alert alert-${type === 'error' ? 'danger' : type} position-fixed`;
                notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
                notification.textContent = message;
                
                document.body.appendChild(notification);
                
                setTimeout(() => {
                    notification.remove();
                }, 3000);
            }
            
            // Additional methods for collaboration, sharing, etc.
            onGridChange(items) {
                // Handle grid changes
            }
            
            onWidgetAdded(items) {
                // Handle widget addition
            }
            
            onWidgetRemoved(items) {
                // Handle widget removal
            }
            
            changeTheme(theme) {
                document.body.className = theme === 'dark' ? 'dark-theme' : '';
            }
            
            previewDashboard() {
                if (this.dashboardId) {
                    window.open(`/dashboard/${this.dashboardId}`, '_blank');
                }
            }
            
            showShareModal() {
                const modal = new bootstrap.Modal(document.getElementById('shareModal'));
                modal.show();
            }
            
            updateUrl() {
                if (this.dashboardId) {
                    const url = new URL(window.location);
                    url.searchParams.set('id', this.dashboardId);
                    window.history.replaceState({}, '', url);
                }
            }
        }
        
        // Initialize dashboard builder when page loads
        let builder;
        document.addEventListener('DOMContentLoaded', () => {
            builder = new DashboardBuilder();
        });
    </script>
</body>
</html>
        '''
    
    def generate_dashboard_css(self) -> str:
        """Generate additional CSS for dashboard components"""
        return '''
        /* Additional Dashboard Styles */
        .dashboard-grid-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-image: 
                linear-gradient(to right, #e0e0e0 1px, transparent 1px),
                linear-gradient(to bottom, #e0e0e0 1px, transparent 1px);
            background-size: 20px 20px;
            pointer-events: none;
            opacity: 0.3;
        }
        
        .widget-loading {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #6c757d;
        }
        
        .widget-error {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #dc3545;
            flex-direction: column;
        }
        
        .collaboration-cursor {
            position: absolute;
            pointer-events: none;
            z-index: 1000;
            transition: all 0.1s ease;
        }
        
        .widget-lock-indicator {
            position: absolute;
            top: 5px;
            right: 5px;
            background: #ffc107;
            color: #000;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        
        .dashboard-minimap {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 200px;
            height: 150px;
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid #dee2e6;
            border-radius: 0.375rem;
            z-index: 1000;
        }
        '''
    
    def generate_dashboard_js(self) -> str:
        """Generate additional JavaScript for dashboard functionality"""
        return '''
        // Additional Dashboard JavaScript
        class DashboardUtils {
            static generateWidgetId() {
                return 'widget_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            }
            
            static formatNumber(num, decimals = 2) {
                return new Intl.NumberFormat('en-US', {
                    minimumFractionDigits: decimals,
                    maximumFractionDigits: decimals
                }).format(num);
            }
            
            static formatCurrency(amount, currency = 'USD') {
                return new Intl.NumberFormat('en-US', {
                    style: 'currency',
                    currency: currency
                }).format(amount);
            }
            
            static formatPercentage(value, decimals = 2) {
                return new Intl.NumberFormat('en-US', {
                    style: 'percent',
                    minimumFractionDigits: decimals,
                    maximumFractionDigits: decimals
                }).format(value / 100);
            }
            
            static debounce(func, wait) {
                let timeout;
                return function executedFunction(...args) {
                    const later = () => {
                        clearTimeout(timeout);
                        func(...args);
                    };
                    clearTimeout(timeout);
                    timeout = setTimeout(later, wait);
                };
            }
            
            static throttle(func, limit) {
                let inThrottle;
                return function() {
                    const args = arguments;
                    const context = this;
                    if (!inThrottle) {
                        func.apply(context, args);
                        inThrottle = true;
                        setTimeout(() => inThrottle = false, limit);
                    }
                }
            }
        }
        
        class WidgetRenderer {
            static renderChart(container, data, config) {
                // Chart rendering logic
                container.innerHTML = '<div class="widget-loading">Loading chart...</div>';
                
                // Simulate async chart loading
                setTimeout(() => {
                    container.innerHTML = `
                        <div class="chart-container">
                            <canvas id="chart-${config.widget_id}"></canvas>
                        </div>
                    `;
                }, 1000);
            }
            
            static renderTable(container, data, config) {
                if (!data || !data.rows) {
                    container.innerHTML = '<div class="widget-error">No data available</div>';
                    return;
                }
                
                let html = '<div class="table-responsive"><table class="table table-sm">';
                
                // Headers
                if (data.columns) {
                    html += '<thead><tr>';
                    data.columns.forEach(col => {
                        html += `<th>${col.title}</th>`;
                    });
                    html += '</tr></thead>';
                }
                
                // Rows
                html += '<tbody>';
                data.rows.slice(0, 10).forEach(row => {
                    html += '<tr>';
                    if (data.columns) {
                        data.columns.forEach(col => {
                            const value = row[col.key];
                            html += `<td>${this.formatCellValue(value, col.type)}</td>`;
                        });
                    }
                    html += '</tr>';
                });
                html += '</tbody></table></div>';
                
                container.innerHTML = html;
            }
            
            static renderMetric(container, data, config) {
                if (!data || data.value === undefined) {
                    container.innerHTML = '<div class="widget-error">No data available</div>';
                    return;
                }
                
                const statusClass = data.status === 'positive' ? 'text-success' : 
                                  data.status === 'negative' ? 'text-danger' : 'text-muted';
                
                const trendIcon = data.trend === 'up' ? 'fa-arrow-up' : 
                                data.trend === 'down' ? 'fa-arrow-down' : 'fa-minus';
                
                container.innerHTML = `
                    <div class="metric-widget text-center">
                        <div class="metric-value ${statusClass}">
                            <h2>${data.formatted_value || data.value}</h2>
                        </div>
                        <div class="metric-trend">
                            <i class="fas ${trendIcon} ${statusClass}"></i>
                            <span class="ms-1">${data.change || ''}</span>
                        </div>
                        <div class="metric-label text-muted">
                            ${config.title}
                        </div>
                    </div>
                `;
            }
            
            static formatCellValue(value, type) {
                if (value === null || value === undefined) return '-';
                
                switch (type) {
                    case 'currency':
                        return DashboardUtils.formatCurrency(value);
                    case 'percentage':
                        return DashboardUtils.formatPercentage(value);
                    case 'number':
                        return DashboardUtils.formatNumber(value);
                    case 'datetime':
                        return new Date(value).toLocaleString();
                    default:
                        return value.toString();
                }
            }
        }
        
        // Export for use in other modules
        if (typeof module !== 'undefined' && module.exports) {
            module.exports = { DashboardUtils, WidgetRenderer };
        }
        '''

def create_dashboard_frontend() -> DashboardFrontend:
    """Create dashboard frontend instance"""
    return DashboardFrontend()

if __name__ == "__main__":
    frontend = create_dashboard_frontend()
    
    # Generate templates
    html_template = frontend.generate_dashboard_builder_html()
    css_styles = frontend.generate_dashboard_css()
    js_code = frontend.generate_dashboard_js()
    
    print("Dashboard frontend components generated successfully")
    print(f"HTML template length: {len(html_template)} characters")
    print(f"CSS styles length: {len(css_styles)} characters")
    print(f"JavaScript code length: {len(js_code)} characters")