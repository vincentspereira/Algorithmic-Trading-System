"""
Dashboard Builder System
Provides drag-and-drop dashboard builder with widget-based architecture,
dashboard sharing, templates, and personalization features.
"""
import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
from pathlib import Path

try:
    from flask import Flask, render_template, jsonify, request, session, send_file
    from flask_socketio import SocketIO, emit, join_room, leave_room
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

from .customizable_dashboard import (
    CustomizableDashboardSystem, Dashboard, WidgetConfig, DashboardLayout,
    DashboardTheme, WidgetType, LayoutType, ThemeType
)

class BuilderMode(Enum):
    """Dashboard builder modes"""
    VIEW = "view"
    EDIT = "edit"
    PREVIEW = "preview"
    SHARE = "share"

class WidgetCategory(Enum):
    """Widget categories for organization"""
    TRADING = "trading"
    ANALYTICS = "analytics"
    RISK = "risk"
    COMPLIANCE = "compliance"
    MARKET_DATA = "market_data"
    PORTFOLIO = "portfolio"
    NEWS = "news"
    CUSTOM = "custom"

@dataclass
class WidgetTemplate:
    """Widget template for dashboard builder"""
    template_id: str
    name: str
    description: str
    category: WidgetCategory
    widget_type: WidgetType
    default_config: WidgetConfig
    preview_image: str = ""
    tags: List[str] = field(default_factory=list)
    is_premium: bool = False

@dataclass
class DashboardPermission:
    """Dashboard sharing permissions"""
    user_id: str
    permission_type: str  # view, edit, admin
    granted_by: str
    granted_at: datetime
    expires_at: Optional[datetime] = None

@dataclass
class DashboardShare:
    """Dashboard sharing configuration"""
    share_id: str
    dashboard_id: str
    share_type: str  # public, private, team
    share_url: str
    permissions: List[DashboardPermission] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    is_active: bool = True

@dataclass
class UserPreferences:
    """User dashboard preferences"""
    user_id: str
    default_theme: str = "light"
    auto_refresh: bool = True
    refresh_interval: int = 30
    grid_snap: bool = True
    show_grid: bool = False
    compact_mode: bool = False
    favorite_widgets: List[str] = field(default_factory=list)
    recent_dashboards: List[str] = field(default_factory=list)
    custom_themes: Dict[str, Any] = field(default_factory=dict)

class DashboardBuilder:
    """Advanced dashboard builder with drag-and-drop functionality"""
    
    def __init__(self, dashboard_system: CustomizableDashboardSystem):
        self.dashboard_system = dashboard_system
        self.logger = logging.getLogger(__name__)
        
        # Widget templates
        self.widget_templates: Dict[str, WidgetTemplate] = {}
        
        # Dashboard sharing
        self.dashboard_shares: Dict[str, DashboardShare] = {}
        
        # User preferences
        self.user_preferences: Dict[str, UserPreferences] = {}
        
        self._initialize_widget_templates()
        self._setup_builder_routes()
        self._setup_builder_socket_events()
    
    def _initialize_widget_templates(self):
        """Initialize widget templates"""
        templates = [
            # Trading widgets
            WidgetTemplate(
                template_id="portfolio_summary",
                name="Portfolio Summary",
                description="Overview of portfolio value and performance",
                category=WidgetCategory.TRADING,
                widget_type=WidgetType.METRIC,
                default_config=WidgetConfig(
                    widget_id="portfolio_summary",
                    widget_type=WidgetType.METRIC,
                    title="Portfolio Summary",
                    data_source="portfolio_value",
                    position={"x": 0, "y": 0, "w": 4, "h": 3}
                ),
                tags=["portfolio", "trading", "summary"]
            ),
            
            WidgetTemplate(
                template_id="positions_table",
                name="Positions Table",
                description="Detailed view of all positions",
                category=WidgetCategory.TRADING,
                widget_type=WidgetType.TABLE,
                default_config=WidgetConfig(
                    widget_id="positions_table",
                    widget_type=WidgetType.TABLE,
                    title="Positions",
                    data_source="positions",
                    position={"x": 0, "y": 3, "w": 8, "h": 4}
                ),
                tags=["positions", "trading", "table"]
            ),
            
            # Analytics widgets
            WidgetTemplate(
                template_id="pnl_chart",
                name="P&L Chart",
                description="Profit and loss over time",
                category=WidgetCategory.ANALYTICS,
                widget_type=WidgetType.CHART,
                default_config=WidgetConfig(
                    widget_id="pnl_chart",
                    widget_type=WidgetType.CHART,
                    title="P&L Chart",
                    data_source="pnl_chart",
                    position={"x": 4, "y": 0, "w": 8, "h": 6}
                ),
                tags=["pnl", "analytics", "chart"]
            ),
            
            WidgetTemplate(
                template_id="performance_metrics",
                name="Performance Metrics",
                description="Key performance indicators",
                category=WidgetCategory.ANALYTICS,
                widget_type=WidgetType.GAUGE,
                default_config=WidgetConfig(
                    widget_id="performance_metrics",
                    widget_type=WidgetType.GAUGE,
                    title="Performance Metrics",
                    data_source="performance_metrics",
                    position={"x": 8, "y": 0, "w": 4, "h": 3}
                ),
                tags=["performance", "analytics", "metrics"]
            ),
            
            # Risk widgets
            WidgetTemplate(
                template_id="risk_dashboard",
                name="Risk Dashboard",
                description="Risk metrics and limits",
                category=WidgetCategory.RISK,
                widget_type=WidgetType.CHART,
                default_config=WidgetConfig(
                    widget_id="risk_dashboard",
                    widget_type=WidgetType.CHART,
                    title="Risk Metrics",
                    data_source="risk_metrics",
                    position={"x": 0, "y": 0, "w": 6, "h": 4}
                ),
                tags=["risk", "var", "limits"]
            ),
            
            # Market data widgets
            WidgetTemplate(
                template_id="watchlist",
                name="Watchlist",
                description="Market watchlist with prices",
                category=WidgetCategory.MARKET_DATA,
                widget_type=WidgetType.WATCHLIST,
                default_config=WidgetConfig(
                    widget_id="watchlist",
                    widget_type=WidgetType.WATCHLIST,
                    title="Watchlist",
                    data_source="watchlist",
                    position={"x": 0, "y": 0, "w": 4, "h": 6}
                ),
                tags=["watchlist", "market", "prices"]
            ),
            
            WidgetTemplate(
                template_id="order_book",
                name="Order Book",
                description="Real-time order book data",
                category=WidgetCategory.MARKET_DATA,
                widget_type=WidgetType.ORDER_BOOK,
                default_config=WidgetConfig(
                    widget_id="order_book",
                    widget_type=WidgetType.ORDER_BOOK,
                    title="Order Book",
                    data_source="order_book",
                    position={"x": 4, "y": 0, "w": 4, "h": 6}
                ),
                tags=["orderbook", "market", "depth"]
            ),
            
            # News widgets
            WidgetTemplate(
                template_id="market_news",
                name="Market News",
                description="Latest market news and updates",
                category=WidgetCategory.NEWS,
                widget_type=WidgetType.NEWS,
                default_config=WidgetConfig(
                    widget_id="market_news",
                    widget_type=WidgetType.NEWS,
                    title="Market News",
                    data_source="market_news",
                    position={"x": 8, "y": 0, "w": 4, "h": 6}
                ),
                tags=["news", "market", "updates"]
            )
        ]
        
        for template in templates:
            self.widget_templates[template.template_id] = template
    
    def _setup_builder_routes(self):
        """Setup dashboard builder routes"""
        app = self.dashboard_system.app
        
        @app.route('/builder')
        def dashboard_builder():
            """Dashboard builder interface"""
            return render_template('dashboard_builder.html',
                                 widget_templates=list(self.widget_templates.values()),
                                 themes=list(self.dashboard_system.themes.values()))
        
        @app.route('/builder/<dashboard_id>')
        def edit_dashboard_builder(dashboard_id):
            """Edit dashboard in builder"""
            dashboard = self.dashboard_system.dashboards.get(dashboard_id)
            if not dashboard:
                return "Dashboard not found", 404
            
            return render_template('dashboard_builder.html',
                                 dashboard=dashboard,
                                 widget_templates=list(self.widget_templates.values()),
                                 themes=list(self.dashboard_system.themes.values()),
                                 mode=BuilderMode.EDIT.value)
        
        @app.route('/api/builder/widget_templates')
        def api_get_widget_templates():
            """Get widget templates"""
            category = request.args.get('category')
            templates = list(self.widget_templates.values())
            
            if category:
                templates = [t for t in templates if t.category.value == category]
            
            return jsonify([asdict(template) for template in templates])
        
        @app.route('/api/builder/create_widget', methods=['POST'])
        def api_create_widget():
            """Create widget from template"""
            try:
                data = request.get_json()
                template_id = data['template_id']
                dashboard_id = data['dashboard_id']
                position = data.get('position', {"x": 0, "y": 0, "w": 4, "h": 3})
                
                template = self.widget_templates.get(template_id)
                if not template:
                    return jsonify({'success': False, 'error': 'Template not found'}), 404
                
                dashboard = self.dashboard_system.dashboards.get(dashboard_id)
                if not dashboard:
                    return jsonify({'success': False, 'error': 'Dashboard not found'}), 404
                
                # Create widget from template
                widget_config = WidgetConfig(
                    widget_id=str(uuid.uuid4()),
                    widget_type=template.widget_type,
                    title=template.name,
                    data_source=template.default_config.data_source,
                    position=position,
                    parameters=template.default_config.parameters.copy(),
                    styling=template.default_config.styling.copy()
                )
                
                dashboard.widgets.append(widget_config)
                dashboard.updated_at = datetime.now()
                
                return jsonify({
                    'success': True,
                    'widget': asdict(widget_config)
                })
            
            except Exception as e:
                self.logger.error(f"Error creating widget: {e}")
                return jsonify({'success': False, 'error': str(e)}), 400
        
        @app.route('/api/builder/update_widget', methods=['PUT'])
        def api_update_widget():
            """Update widget configuration"""
            try:
                data = request.get_json()
                dashboard_id = data['dashboard_id']
                widget_id = data['widget_id']
                updates = data['updates']
                
                dashboard = self.dashboard_system.dashboards.get(dashboard_id)
                if not dashboard:
                    return jsonify({'success': False, 'error': 'Dashboard not found'}), 404
                
                # Find and update widget
                for widget in dashboard.widgets:
                    if widget.widget_id == widget_id:
                        for key, value in updates.items():
                            if hasattr(widget, key):
                                setattr(widget, key, value)
                        
                        dashboard.updated_at = datetime.now()
                        
                        return jsonify({
                            'success': True,
                            'widget': asdict(widget)
                        })
                
                return jsonify({'success': False, 'error': 'Widget not found'}), 404
            
            except Exception as e:
                self.logger.error(f"Error updating widget: {e}")
                return jsonify({'success': False, 'error': str(e)}), 400
        
        @app.route('/api/builder/delete_widget', methods=['DELETE'])
        def api_delete_widget():
            """Delete widget from dashboard"""
            try:
                data = request.get_json()
                dashboard_id = data['dashboard_id']
                widget_id = data['widget_id']
                
                dashboard = self.dashboard_system.dashboards.get(dashboard_id)
                if not dashboard:
                    return jsonify({'success': False, 'error': 'Dashboard not found'}), 404
                
                # Remove widget
                dashboard.widgets = [w for w in dashboard.widgets if w.widget_id != widget_id]
                dashboard.updated_at = datetime.now()
                
                return jsonify({'success': True})
            
            except Exception as e:
                self.logger.error(f"Error deleting widget: {e}")
                return jsonify({'success': False, 'error': str(e)}), 400
        
        @app.route('/api/builder/save_layout', methods=['POST'])
        def api_save_layout():
            """Save dashboard layout"""
            try:
                data = request.get_json()
                dashboard_id = data['dashboard_id']
                layout_data = data['layout']
                
                dashboard = self.dashboard_system.dashboards.get(dashboard_id)
                if not dashboard:
                    return jsonify({'success': False, 'error': 'Dashboard not found'}), 404
                
                # Update widget positions
                for widget_data in layout_data:
                    widget_id = widget_data['widget_id']
                    position = widget_data['position']
                    
                    for widget in dashboard.widgets:
                        if widget.widget_id == widget_id:
                            widget.position = position
                            break
                
                dashboard.updated_at = datetime.now()
                
                return jsonify({'success': True})
            
            except Exception as e:
                self.logger.error(f"Error saving layout: {e}")
                return jsonify({'success': False, 'error': str(e)}), 400
        
        @app.route('/api/builder/user_preferences/<user_id>')
        def api_get_user_preferences(user_id):
            """Get user preferences"""
            preferences = self.user_preferences.get(user_id, UserPreferences(user_id=user_id))
            return jsonify(asdict(preferences))
        
        @app.route('/api/builder/user_preferences/<user_id>', methods=['PUT'])
        def api_update_user_preferences(user_id):
            """Update user preferences"""
            try:
                data = request.get_json()
                
                if user_id not in self.user_preferences:
                    self.user_preferences[user_id] = UserPreferences(user_id=user_id)
                
                preferences = self.user_preferences[user_id]
                
                for key, value in data.items():
                    if hasattr(preferences, key):
                        setattr(preferences, key, value)
                
                return jsonify({
                    'success': True,
                    'preferences': asdict(preferences)
                })
            
            except Exception as e:
                self.logger.error(f"Error updating preferences: {e}")
                return jsonify({'success': False, 'error': str(e)}), 400
    
    def _setup_builder_socket_events(self):
        """Setup dashboard builder socket events"""
        socketio = self.dashboard_system.socketio
        
        @socketio.on('join_builder')
        def handle_join_builder(data):
            """Join dashboard builder room"""
            dashboard_id = data.get('dashboard_id')
            if dashboard_id:
                join_room(f"builder_{dashboard_id}")
                emit('joined_builder', {'dashboard_id': dashboard_id})
        
        @socketio.on('leave_builder')
        def handle_leave_builder(data):
            """Leave dashboard builder room"""
            dashboard_id = data.get('dashboard_id')
            if dashboard_id:
                leave_room(f"builder_{dashboard_id}")
                emit('left_builder', {'dashboard_id': dashboard_id})
        
        @socketio.on('widget_drag_start')
        def handle_widget_drag_start(data):
            """Handle widget drag start"""
            dashboard_id = data.get('dashboard_id')
            widget_id = data.get('widget_id')
            
            if dashboard_id and widget_id:
                emit('widget_drag_started', {
                    'dashboard_id': dashboard_id,
                    'widget_id': widget_id,
                    'user_id': data.get('user_id')
                }, room=f"builder_{dashboard_id}", include_self=False)
        
        @socketio.on('widget_drag_end')
        def handle_widget_drag_end(data):
            """Handle widget drag end"""
            dashboard_id = data.get('dashboard_id')
            widget_id = data.get('widget_id')
            new_position = data.get('position')
            
            if dashboard_id and widget_id and new_position:
                # Update widget position
                dashboard = self.dashboard_system.dashboards.get(dashboard_id)
                if dashboard:
                    for widget in dashboard.widgets:
                        if widget.widget_id == widget_id:
                            widget.position = new_position
                            break
                    
                    dashboard.updated_at = datetime.now()
                
                emit('widget_drag_ended', {
                    'dashboard_id': dashboard_id,
                    'widget_id': widget_id,
                    'position': new_position
                }, room=f"builder_{dashboard_id}")
        
        @socketio.on('widget_resize')
        def handle_widget_resize(data):
            """Handle widget resize"""
            dashboard_id = data.get('dashboard_id')
            widget_id = data.get('widget_id')
            new_size = data.get('size')
            
            if dashboard_id and widget_id and new_size:
                # Update widget size
                dashboard = self.dashboard_system.dashboards.get(dashboard_id)
                if dashboard:
                    for widget in dashboard.widgets:
                        if widget.widget_id == widget_id:
                            widget.position.update(new_size)
                            break
                    
                    dashboard.updated_at = datetime.now()
                
                emit('widget_resized', {
                    'dashboard_id': dashboard_id,
                    'widget_id': widget_id,
                    'size': new_size
                }, room=f"builder_{dashboard_id}")
        
        @socketio.on('collaborative_edit')
        def handle_collaborative_edit(data):
            """Handle collaborative editing"""
            dashboard_id = data.get('dashboard_id')
            edit_type = data.get('edit_type')
            edit_data = data.get('edit_data')
            user_id = data.get('user_id')
            
            if dashboard_id and edit_type:
                emit('collaborative_edit_update', {
                    'dashboard_id': dashboard_id,
                    'edit_type': edit_type,
                    'edit_data': edit_data,
                    'user_id': user_id,
                    'timestamp': datetime.now().isoformat()
                }, room=f"builder_{dashboard_id}", include_self=False)
    
    def create_dashboard_share(self, dashboard_id: str, share_type: str, 
                             created_by: str, expires_hours: Optional[int] = None) -> DashboardShare:
        """Create dashboard share"""
        share_id = str(uuid.uuid4())
        share_url = f"/shared/{share_id}"
        
        expires_at = None
        if expires_hours:
            expires_at = datetime.now() + timedelta(hours=expires_hours)
        
        share = DashboardShare(
            share_id=share_id,
            dashboard_id=dashboard_id,
            share_type=share_type,
            share_url=share_url,
            expires_at=expires_at
        )
        
        self.dashboard_shares[share_id] = share
        
        return share
    
    def add_dashboard_permission(self, share_id: str, user_id: str, 
                               permission_type: str, granted_by: str) -> bool:
        """Add dashboard permission"""
        share = self.dashboard_shares.get(share_id)
        if not share:
            return False
        
        permission = DashboardPermission(
            user_id=user_id,
            permission_type=permission_type,
            granted_by=granted_by,
            granted_at=datetime.now()
        )
        
        share.permissions.append(permission)
        return True
    
    def get_user_dashboard_access(self, user_id: str, dashboard_id: str) -> Optional[str]:
        """Get user's access level to dashboard"""
        # Check if user owns the dashboard
        dashboard = self.dashboard_system.dashboards.get(dashboard_id)
        if dashboard and dashboard.owner_id == user_id:
            return "admin"
        
        # Check shared access
        for share in self.dashboard_shares.values():
            if share.dashboard_id == dashboard_id and share.is_active:
                if share.expires_at and share.expires_at < datetime.now():
                    continue
                
                if share.share_type == "public":
                    return "view"
                
                for permission in share.permissions:
                    if permission.user_id == user_id:
                        if permission.expires_at and permission.expires_at < datetime.now():
                            continue
                        return permission.permission_type
        
        return None
    
    def export_dashboard(self, dashboard_id: str) -> Dict[str, Any]:
        """Export dashboard configuration"""
        dashboard = self.dashboard_system.dashboards.get(dashboard_id)
        if not dashboard:
            return {}
        
        export_data = {
            "dashboard": asdict(dashboard),
            "export_version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "widgets": [asdict(widget) for widget in dashboard.widgets],
            "layout": asdict(dashboard.layout) if dashboard.layout else None,
            "theme": asdict(dashboard.theme) if dashboard.theme else None
        }
        
        return export_data
    
    def import_dashboard(self, import_data: Dict[str, Any], owner_id: str) -> Optional[str]:
        """Import dashboard configuration"""
        try:
            dashboard_data = import_data["dashboard"]
            
            # Create new dashboard
            new_dashboard_id = str(uuid.uuid4())
            dashboard = Dashboard(
                dashboard_id=new_dashboard_id,
                name=f"{dashboard_data['name']} (Imported)",
                description=dashboard_data.get('description', ''),
                owner_id=owner_id,
                widgets=[],
                tags=dashboard_data.get('tags', [])
            )
            
            # Import widgets
            for widget_data in import_data.get("widgets", []):
                widget = WidgetConfig(
                    widget_id=str(uuid.uuid4()),  # Generate new ID
                    widget_type=WidgetType(widget_data['widget_type']),
                    title=widget_data['title'],
                    data_source=widget_data['data_source'],
                    position=widget_data['position'],
                    parameters=widget_data.get('parameters', {}),
                    styling=widget_data.get('styling', {})
                )
                dashboard.widgets.append(widget)
            
            # Import layout
            if import_data.get("layout"):
                layout_data = import_data["layout"]
                dashboard.layout = DashboardLayout(
                    layout_id=str(uuid.uuid4()),
                    layout_type=LayoutType(layout_data['layout_type']),
                    grid_columns=layout_data.get('grid_columns', 12),
                    grid_rows=layout_data.get('grid_rows', 20)
                )
            
            # Import theme
            if import_data.get("theme"):
                theme_data = import_data["theme"]
                dashboard.theme = DashboardTheme(
                    theme_id=str(uuid.uuid4()),
                    theme_type=ThemeType(theme_data['theme_type']),
                    name=theme_data['name'],
                    colors=theme_data.get('colors', {}),
                    fonts=theme_data.get('fonts', {})
                )
            
            self.dashboard_system.dashboards[new_dashboard_id] = dashboard
            
            return new_dashboard_id
        
        except Exception as e:
            self.logger.error(f"Error importing dashboard: {e}")
            return None
    
    def get_dashboard_analytics(self, dashboard_id: str) -> Dict[str, Any]:
        """Get dashboard usage analytics"""
        dashboard = self.dashboard_system.dashboards.get(dashboard_id)
        if not dashboard:
            return {}
        
        # In a real implementation, this would query actual usage data
        analytics = {
            "dashboard_id": dashboard_id,
            "total_views": 150 + hash(dashboard_id) % 500,
            "unique_viewers": 25 + hash(dashboard_id) % 100,
            "avg_session_duration": 300 + hash(dashboard_id) % 600,  # seconds
            "most_used_widgets": [
                {"widget_type": "chart", "usage_count": 45},
                {"widget_type": "table", "usage_count": 32},
                {"widget_type": "metric", "usage_count": 28}
            ],
            "peak_usage_hours": [9, 10, 11, 14, 15, 16],
            "last_accessed": (datetime.now() - timedelta(hours=2)).isoformat(),
            "performance_metrics": {
                "avg_load_time": 1.2,  # seconds
                "error_rate": 0.02,    # percentage
                "uptime": 99.8         # percentage
            }
        }
        
        return analytics

def create_dashboard_builder(dashboard_system: CustomizableDashboardSystem) -> DashboardBuilder:
    """Create dashboard builder instance"""
    return DashboardBuilder(dashboard_system)

if __name__ == "__main__":
    # Example usage
    from .customizable_dashboard import create_dashboard_system
    
    dashboard_system = create_dashboard_system()
    builder = create_dashboard_builder(dashboard_system)
    
    print("Dashboard builder created successfully")
    print(f"Available widget templates: {len(builder.widget_templates)}")
    
    # Create a sample dashboard
    dashboard_data = {
        'name': 'Sample Trading Dashboard',
        'description': 'A sample dashboard for testing',
        'owner_id': 'user_123',
        'tags': ['trading', 'sample']
    }
    
    # This would normally be done through the API
    print("Dashboard builder ready for use")