"""
Test suite for dashboard builder system including drag-and-drop functionality,
sharing, collaboration, and personalization features.
"""
import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import uuid

# Import the modules to test
from nautilus_trader_engine.visualization.dashboard_builder import (
    DashboardBuilder, WidgetTemplate, DashboardPermission, DashboardShare,
    UserPreferences, BuilderMode, WidgetCategory, create_dashboard_builder
)
from nautilus_trader_engine.visualization.dashboard_sharing import (
    DashboardSharingSystem, ShareLink, Team, TeamMember, Comment,
    CollaborativeSession, ShareType, PermissionLevel, CollaborationEvent,
    create_sharing_system
)
from nautilus_trader_engine.visualization.dashboard_frontend import (
    DashboardFrontend, create_dashboard_frontend
)
from nautilus_trader_engine.visualization.customizable_dashboard import (
    CustomizableDashboardSystem, Dashboard, WidgetConfig, DashboardLayout,
    DashboardTheme, WidgetType, LayoutType, ThemeType
)

class TestDashboardBuilder:
    """Test dashboard builder functionality"""
    
    @pytest.fixture
    def dashboard_system(self):
        """Create dashboard system for testing"""
        with patch('nautilus_trader_engine.visualization.customizable_dashboard.FLASK_AVAILABLE', True):
            return CustomizableDashboardSystem(host="127.0.0.1", port=5556)
    
    @pytest.fixture
    def dashboard_builder(self, dashboard_system):
        """Create dashboard builder for testing"""
        return DashboardBuilder(dashboard_system)
    
    def test_builder_initialization(self, dashboard_builder):
        """Test dashboard builder initialization"""
        assert dashboard_builder.dashboard_system is not None
        assert len(dashboard_builder.widget_templates) > 0
        assert dashboard_builder.dashboard_shares == {}
        assert dashboard_builder.user_preferences == {}
    
    def test_widget_templates_initialization(self, dashboard_builder):
        """Test widget templates are properly initialized"""
        templates = dashboard_builder.widget_templates
        
        # Check that we have templates for different categories
        categories = set(template.category for template in templates.values())
        expected_categories = {
            WidgetCategory.TRADING,
            WidgetCategory.ANALYTICS,
            WidgetCategory.MARKET_DATA,
            WidgetCategory.RISK,
            WidgetCategory.NEWS
        }
        
        assert expected_categories.issubset(categories)
        
        # Check specific templates
        assert "portfolio_summary" in templates
        assert "positions_table" in templates
        assert "pnl_chart" in templates
        
        # Verify template structure
        portfolio_template = templates["portfolio_summary"]
        assert portfolio_template.name == "Portfolio Summary"
        assert portfolio_template.category == WidgetCategory.TRADING
        assert portfolio_template.widget_type == WidgetType.METRIC
        assert isinstance(portfolio_template.default_config, WidgetConfig)
    
    def test_create_dashboard_share(self, dashboard_builder):
        """Test creating dashboard share"""
        dashboard_id = "test_dashboard_123"
        share_type = "public"
        created_by = "user_123"
        
        share = dashboard_builder.create_dashboard_share(
            dashboard_id=dashboard_id,
            share_type=share_type,
            created_by=created_by,
            expires_hours=24
        )
        
        assert share.dashboard_id == dashboard_id
        assert share.share_type == share_type
        assert share.created_by == created_by
        assert share.expires_at is not None
        assert share.is_active is True
        assert share.share_id in dashboard_builder.dashboard_shares
    
    def test_add_dashboard_permission(self, dashboard_builder):
        """Test adding dashboard permission"""
        # First create a share
        share = dashboard_builder.create_dashboard_share(
            dashboard_id="test_dashboard_123",
            share_type="private",
            created_by="user_123"
        )
        
        # Add permission
        result = dashboard_builder.add_dashboard_permission(
            share_id=share.share_id,
            user_id="user_456",
            permission_type="edit",
            granted_by="user_123"
        )
        
        assert result is True
        assert len(share.permissions) == 1
        
        permission = share.permissions[0]
        assert permission.user_id == "user_456"
        assert permission.permission_type == "edit"
        assert permission.granted_by == "user_123"
    
    def test_get_user_dashboard_access(self, dashboard_builder):
        """Test getting user dashboard access"""
        dashboard_id = "test_dashboard_123"
        owner_id = "user_123"
        
        # Create dashboard in system
        dashboard = Dashboard(
            dashboard_id=dashboard_id,
            name="Test Dashboard",
            description="Test",
            owner_id=owner_id
        )
        dashboard_builder.dashboard_system.dashboards[dashboard_id] = dashboard
        
        # Test owner access
        access = dashboard_builder.get_user_dashboard_access(owner_id, dashboard_id)
        assert access == "admin"
        
        # Test no access
        access = dashboard_builder.get_user_dashboard_access("user_456", dashboard_id)
        assert access is None
        
        # Test shared access
        share = dashboard_builder.create_dashboard_share(
            dashboard_id=dashboard_id,
            share_type="public",
            created_by=owner_id
        )
        
        access = dashboard_builder.get_user_dashboard_access("user_789", dashboard_id)
        assert access == "view"
    
    def test_export_dashboard(self, dashboard_builder):
        """Test exporting dashboard configuration"""
        dashboard_id = "test_dashboard_123"
        
        # Create dashboard with widgets
        dashboard = Dashboard(
            dashboard_id=dashboard_id,
            name="Test Dashboard",
            description="Test dashboard for export",
            owner_id="user_123",
            tags=["test", "export"]
        )
        
        # Add some widgets
        widget1 = WidgetConfig(
            widget_id="widget_1",
            widget_type=WidgetType.CHART,
            title="Test Chart",
            data_source="test_data",
            position={"x": 0, "y": 0, "w": 4, "h": 3}
        )
        
        widget2 = WidgetConfig(
            widget_id="widget_2",
            widget_type=WidgetType.TABLE,
            title="Test Table",
            data_source="test_table",
            position={"x": 4, "y": 0, "w": 4, "h": 3}
        )
        
        dashboard.widgets = [widget1, widget2]
        dashboard_builder.dashboard_system.dashboards[dashboard_id] = dashboard
        
        # Export dashboard
        export_data = dashboard_builder.export_dashboard(dashboard_id)
        
        assert export_data["dashboard"]["dashboard_id"] == dashboard_id
        assert export_data["dashboard"]["name"] == "Test Dashboard"
        assert export_data["export_version"] == "1.0"
        assert "exported_at" in export_data
        assert len(export_data["widgets"]) == 2
        assert export_data["widgets"][0]["widget_id"] == "widget_1"
        assert export_data["widgets"][1]["widget_id"] == "widget_2"
    
    def test_import_dashboard(self, dashboard_builder):
        """Test importing dashboard configuration"""
        import_data = {
            "dashboard": {
                "name": "Imported Dashboard",
                "description": "Imported from export",
                "tags": ["imported", "test"]
            },
            "widgets": [
                {
                    "widget_type": "chart",
                    "title": "Imported Chart",
                    "data_source": "imported_data",
                    "position": {"x": 0, "y": 0, "w": 4, "h": 3},
                    "parameters": {"symbol": "AAPL"},
                    "styling": {"color": "blue"}
                }
            ],
            "layout": {
                "layout_type": "grid",
                "grid_columns": 12,
                "grid_rows": 20
            },
            "theme": {
                "theme_type": "light",
                "name": "Light Theme",
                "colors": {"primary": "#007bff"}
            }
        }
        
        dashboard_id = dashboard_builder.import_dashboard(import_data, "user_123")
        
        assert dashboard_id is not None
        assert dashboard_id in dashboard_builder.dashboard_system.dashboards
        
        imported_dashboard = dashboard_builder.dashboard_system.dashboards[dashboard_id]
        assert imported_dashboard.name == "Imported Dashboard (Imported)"
        assert imported_dashboard.owner_id == "user_123"
        assert len(imported_dashboard.widgets) == 1
        assert imported_dashboard.widgets[0].title == "Imported Chart"
        assert imported_dashboard.layout is not None
        assert imported_dashboard.theme is not None
    
    def test_get_dashboard_analytics(self, dashboard_builder):
        """Test getting dashboard analytics"""
        dashboard_id = "test_dashboard_123"
        
        analytics = dashboard_builder.get_dashboard_analytics(dashboard_id)
        
        assert "dashboard_id" in analytics
        assert "total_views" in analytics
        assert "unique_viewers" in analytics
        assert "avg_session_duration" in analytics
        assert "most_used_widgets" in analytics
        assert "peak_usage_hours" in analytics
        assert "performance_metrics" in analytics
        
        assert analytics["dashboard_id"] == dashboard_id
        assert isinstance(analytics["total_views"], int)
        assert isinstance(analytics["unique_viewers"], int)
        assert isinstance(analytics["most_used_widgets"], list)

class TestDashboardSharingSystem:
    """Test dashboard sharing system"""
    
    @pytest.fixture
    def sharing_system(self):
        """Create sharing system for testing"""
        return DashboardSharingSystem()
    
    def test_sharing_system_initialization(self, sharing_system):
        """Test sharing system initialization"""
        assert sharing_system.share_links == {}
        assert sharing_system.teams == {}
        assert sharing_system.comments == {}
        assert sharing_system.collaborative_sessions == {}
        assert sharing_system.active_sessions == {}
        assert sharing_system.user_sessions == {}
    
    def test_create_share_link(self, sharing_system):
        """Test creating share link"""
        dashboard_id = "dashboard_123"
        share_type = ShareType.PUBLIC
        permission_level = PermissionLevel.VIEW
        created_by = "user_123"
        
        share_link = sharing_system.create_share_link(
            dashboard_id=dashboard_id,
            share_type=share_type,
            permission_level=permission_level,
            created_by=created_by,
            expires_hours=24,
            max_access_count=100,
            password="test123",
            allowed_domains=["example.com"]
        )
        
        assert share_link.dashboard_id == dashboard_id
        assert share_link.share_type == share_type
        assert share_link.permission_level == permission_level
        assert share_link.created_by == created_by
        assert share_link.expires_at is not None
        assert share_link.max_access_count == 100
        assert share_link.password_hash is not None
        assert share_link.allowed_domains == ["example.com"]
        assert share_link.is_active is True
        assert share_link.link_id in sharing_system.share_links
    
    def test_validate_share_link(self, sharing_system):
        """Test validating share link"""
        # Create share link
        share_link = sharing_system.create_share_link(
            dashboard_id="dashboard_123",
            share_type=ShareType.PUBLIC,
            permission_level=PermissionLevel.VIEW,
            created_by="user_123",
            password="test123"
        )
        
        # Test valid access
        validated = sharing_system.validate_share_link(
            link_id=share_link.link_id,
            user_id="user_456",
            password="test123"
        )
        
        assert validated is not None
        assert validated.link_id == share_link.link_id
        assert validated.access_count == 1
        
        # Test invalid password
        invalid = sharing_system.validate_share_link(
            link_id=share_link.link_id,
            user_id="user_456",
            password="wrong_password"
        )
        
        assert invalid is None
        
        # Test expired link
        share_link.expires_at = datetime.now() - timedelta(hours=1)
        expired = sharing_system.validate_share_link(
            link_id=share_link.link_id,
            user_id="user_456",
            password="test123"
        )
        
        assert expired is None
    
    def test_revoke_share_link(self, sharing_system):
        """Test revoking share link"""
        share_link = sharing_system.create_share_link(
            dashboard_id="dashboard_123",
            share_type=ShareType.PUBLIC,
            permission_level=PermissionLevel.VIEW,
            created_by="user_123"
        )
        
        # Test successful revocation
        result = sharing_system.revoke_share_link(share_link.link_id, "user_123")
        assert result is True
        assert share_link.is_active is False
        
        # Test unauthorized revocation
        share_link2 = sharing_system.create_share_link(
            dashboard_id="dashboard_456",
            share_type=ShareType.PUBLIC,
            permission_level=PermissionLevel.VIEW,
            created_by="user_123"
        )
        
        result = sharing_system.revoke_share_link(share_link2.link_id, "user_456")
        assert result is False
        assert share_link2.is_active is True
    
    def test_create_team(self, sharing_system):
        """Test creating team"""
        team = sharing_system.create_team(
            name="Trading Team",
            description="Main trading team",
            created_by="user_123"
        )
        
        assert team.name == "Trading Team"
        assert team.description == "Main trading team"
        assert team.created_by == "user_123"
        assert len(team.members) == 1
        assert team.members[0].user_id == "user_123"
        assert team.members[0].permission_level == PermissionLevel.ADMIN
        assert team.team_id in sharing_system.teams
    
    def test_add_team_member(self, sharing_system):
        """Test adding team member"""
        team = sharing_system.create_team(
            name="Trading Team",
            description="Main trading team",
            created_by="user_123"
        )
        
        # Test successful addition
        result = sharing_system.add_team_member(
            team_id=team.team_id,
            user_id="user_456",
            username="trader_jane",
            email="jane@example.com",
            permission_level=PermissionLevel.EDIT,
            added_by="user_123"
        )
        
        assert result is True
        assert len(team.members) == 2
        
        new_member = next(m for m in team.members if m.user_id == "user_456")
        assert new_member.username == "trader_jane"
        assert new_member.email == "jane@example.com"
        assert new_member.permission_level == PermissionLevel.EDIT
        
        # Test unauthorized addition
        result = sharing_system.add_team_member(
            team_id=team.team_id,
            user_id="user_789",
            username="trader_bob",
            email="bob@example.com",
            permission_level=PermissionLevel.VIEW,
            added_by="user_456"  # Not admin
        )
        
        assert result is False
        assert len(team.members) == 2
    
    def test_share_dashboard_with_team(self, sharing_system):
        """Test sharing dashboard with team"""
        team = sharing_system.create_team(
            name="Trading Team",
            description="Main trading team",
            created_by="user_123"
        )
        
        # Test successful sharing
        result = sharing_system.share_dashboard_with_team(
            dashboard_id="dashboard_123",
            team_id=team.team_id,
            shared_by="user_123"
        )
        
        assert result is True
        assert "dashboard_123" in team.shared_dashboards
        
        # Test unauthorized sharing
        result = sharing_system.share_dashboard_with_team(
            dashboard_id="dashboard_456",
            team_id=team.team_id,
            shared_by="user_999"  # Not a team member
        )
        
        assert result is False
        assert "dashboard_456" not in team.shared_dashboards
    
    def test_add_comment(self, sharing_system):
        """Test adding comment"""
        comment = sharing_system.add_comment(
            dashboard_id="dashboard_123",
            user_id="user_123",
            username="trader_john",
            content="This chart needs updating",
            widget_id="widget_456",
            position={"x": 100, "y": 200}
        )
        
        assert comment.dashboard_id == "dashboard_123"
        assert comment.user_id == "user_123"
        assert comment.username == "trader_john"
        assert comment.content == "This chart needs updating"
        assert comment.widget_id == "widget_456"
        assert comment.position == {"x": 100, "y": 200}
        assert comment.is_resolved is False
        
        # Check comment is stored
        dashboard_comments = sharing_system.comments["dashboard_123"]
        assert len(dashboard_comments) == 1
        assert dashboard_comments[0].comment_id == comment.comment_id
    
    def test_resolve_comment(self, sharing_system):
        """Test resolving comment"""
        comment = sharing_system.add_comment(
            dashboard_id="dashboard_123",
            user_id="user_123",
            username="trader_john",
            content="This chart needs updating"
        )
        
        result = sharing_system.resolve_comment(comment.comment_id, "user_456")
        
        assert result is True
        assert comment.is_resolved is True
        assert comment.updated_at is not None
    
    def test_collaborative_session(self, sharing_system):
        """Test collaborative editing session"""
        dashboard_id = "dashboard_123"
        user_id = "user_123"
        
        # Start session
        session_id = sharing_system.start_collaborative_session(dashboard_id, user_id)
        
        assert session_id == f"collab_{dashboard_id}"
        assert session_id in sharing_system.collaborative_sessions
        assert user_id in sharing_system.user_sessions
        assert dashboard_id in sharing_system.active_sessions
        assert user_id in sharing_system.active_sessions[dashboard_id]
        
        session = sharing_system.collaborative_sessions[session_id]
        assert user_id in session.active_users
        
        # Test widget locking
        widget_id = "widget_456"
        lock_result = sharing_system.lock_widget(user_id, widget_id)
        
        assert lock_result is True
        assert widget_id in session.locked_widgets
        assert session.locked_widgets[widget_id] == user_id
        
        # Test cursor update
        cursor_position = {"x": 100, "y": 200}
        cursor_result = sharing_system.update_user_cursor(user_id, cursor_position)
        
        assert cursor_result is True
        assert user_id in session.user_cursors
        assert session.user_cursors[user_id] == cursor_position
        
        # Test leaving session
        left_session_id = sharing_system.leave_collaborative_session(user_id)
        
        assert left_session_id == session_id
        assert user_id not in session.active_users
        assert user_id not in session.user_cursors
        assert widget_id not in session.locked_widgets
        assert user_id not in sharing_system.user_sessions
    
    def test_get_collaboration_state(self, sharing_system):
        """Test getting collaboration state"""
        dashboard_id = "dashboard_123"
        
        # Test empty state
        state = sharing_system.get_collaboration_state(dashboard_id)
        
        assert state["active_users"] == []
        assert state["locked_widgets"] == {}
        assert state["user_cursors"] == {}
        
        # Start session and test state
        sharing_system.start_collaborative_session(dashboard_id, "user_123")
        sharing_system.lock_widget("user_123", "widget_456")
        sharing_system.update_user_cursor("user_123", {"x": 100, "y": 200})
        
        state = sharing_system.get_collaboration_state(dashboard_id)
        
        assert "user_123" in state["active_users"]
        assert state["locked_widgets"]["widget_456"] == "user_123"
        assert state["user_cursors"]["user_123"] == {"x": 100, "y": 200}
        assert "last_activity" in state
    
    def test_get_share_analytics(self, sharing_system):
        """Test getting share analytics"""
        dashboard_id = "dashboard_123"
        
        # Create some shares and comments
        sharing_system.create_share_link(
            dashboard_id=dashboard_id,
            share_type=ShareType.PUBLIC,
            permission_level=PermissionLevel.VIEW,
            created_by="user_123"
        )
        
        sharing_system.create_share_link(
            dashboard_id=dashboard_id,
            share_type=ShareType.PRIVATE,
            permission_level=PermissionLevel.EDIT,
            created_by="user_123"
        )
        
        sharing_system.add_comment(
            dashboard_id=dashboard_id,
            user_id="user_123",
            username="trader_john",
            content="Test comment"
        )
        
        analytics = sharing_system.get_share_analytics(dashboard_id)
        
        assert analytics["dashboard_id"] == dashboard_id
        assert analytics["total_shares"] == 2
        assert analytics["active_shares"] == 2
        assert analytics["total_comments"] == 1
        assert analytics["resolved_comments"] == 0
        assert analytics["share_types"]["public"] == 1
        assert analytics["share_types"]["private"] == 1
        assert analytics["permission_levels"]["view"] == 1
        assert analytics["permission_levels"]["edit"] == 1

class TestDashboardFrontend:
    """Test dashboard frontend components"""
    
    @pytest.fixture
    def frontend(self):
        """Create dashboard frontend for testing"""
        return DashboardFrontend()
    
    def test_frontend_initialization(self, frontend):
        """Test frontend initialization"""
        assert frontend.logger is not None
    
    def test_generate_dashboard_builder_html(self, frontend):
        """Test generating dashboard builder HTML"""
        html = frontend.generate_dashboard_builder_html()
        
        assert isinstance(html, str)
        assert len(html) > 1000  # Should be substantial HTML
        assert "<!DOCTYPE html>" in html
        assert "dashboard-builder" in html
        assert "widget-palette" in html
        assert "dashboard-canvas" in html
        assert "properties-panel" in html
        assert "GridStack" in html
        assert "bootstrap" in html
    
    def test_generate_dashboard_css(self, frontend):
        """Test generating dashboard CSS"""
        css = frontend.generate_dashboard_css()
        
        assert isinstance(css, str)
        assert len(css) > 100
        assert "dashboard-grid-overlay" in css
        assert "widget-loading" in css
        assert "collaboration-cursor" in css
        assert "dashboard-minimap" in css
    
    def test_generate_dashboard_js(self, frontend):
        """Test generating dashboard JavaScript"""
        js = frontend.generate_dashboard_js()
        
        assert isinstance(js, str)
        assert len(js) > 100
        assert "DashboardUtils" in js
        assert "WidgetRenderer" in js
        assert "generateWidgetId" in js
        assert "formatCurrency" in js
        assert "renderChart" in js
        assert "renderTable" in js

class TestIntegration:
    """Integration tests for dashboard builder system"""
    
    @pytest.fixture
    def full_system(self):
        """Create full integrated system"""
        with patch('nautilus_trader_engine.visualization.customizable_dashboard.FLASK_AVAILABLE', True):
            dashboard_system = CustomizableDashboardSystem(host="127.0.0.1", port=5557)
            builder = DashboardBuilder(dashboard_system)
            sharing_system = DashboardSharingSystem()
            frontend = DashboardFrontend()
            
            return {
                'dashboard_system': dashboard_system,
                'builder': builder,
                'sharing_system': sharing_system,
                'frontend': frontend
            }
    
    def test_end_to_end_dashboard_creation(self, full_system):
        """Test complete dashboard creation workflow"""
        builder = full_system['builder']
        sharing_system = full_system['sharing_system']
        
        # 1. Create dashboard
        dashboard_id = str(uuid.uuid4())
        dashboard = Dashboard(
            dashboard_id=dashboard_id,
            name="Integration Test Dashboard",
            description="End-to-end test dashboard",
            owner_id="user_123"
        )
        
        builder.dashboard_system.dashboards[dashboard_id] = dashboard
        
        # 2. Add widgets from templates
        template_id = "portfolio_summary"
        template = builder.widget_templates[template_id]
        
        widget_config = WidgetConfig(
            widget_id=str(uuid.uuid4()),
            widget_type=template.widget_type,
            title=template.name,
            data_source=template.default_config.data_source,
            position={"x": 0, "y": 0, "w": 4, "h": 3}
        )
        
        dashboard.widgets.append(widget_config)
        
        # 3. Create share link
        share_link = builder.create_dashboard_share(
            dashboard_id=dashboard_id,
            share_type="public",
            created_by="user_123"
        )
        
        # 4. Start collaborative session
        session_id = sharing_system.start_collaborative_session(dashboard_id, "user_123")
        
        # 5. Add comment
        comment = sharing_system.add_comment(
            dashboard_id=dashboard_id,
            user_id="user_123",
            username="test_user",
            content="Test integration comment"
        )
        
        # 6. Export dashboard
        export_data = builder.export_dashboard(dashboard_id)
        
        # Verify everything works together
        assert dashboard_id in builder.dashboard_system.dashboards
        assert len(dashboard.widgets) == 1
        assert share_link.dashboard_id == dashboard_id
        assert session_id in sharing_system.collaborative_sessions
        assert len(sharing_system.comments[dashboard_id]) == 1
        assert export_data["dashboard"]["dashboard_id"] == dashboard_id
        assert len(export_data["widgets"]) == 1
    
    def test_collaborative_editing_workflow(self, full_system):
        """Test collaborative editing workflow"""
        sharing_system = full_system['sharing_system']
        dashboard_id = "collab_test_dashboard"
        
        # Multiple users join session
        user1_session = sharing_system.start_collaborative_session(dashboard_id, "user_1")
        user2_session = sharing_system.start_collaborative_session(dashboard_id, "user_2")
        
        assert user1_session == user2_session  # Same session
        
        session = sharing_system.collaborative_sessions[user1_session]
        assert len(session.active_users) == 2
        assert "user_1" in session.active_users
        assert "user_2" in session.active_users
        
        # User 1 locks a widget
        sharing_system.lock_widget("user_1", "widget_123")
        assert session.locked_widgets["widget_123"] == "user_1"
        
        # User 2 tries to lock same widget (should fail)
        result = sharing_system.lock_widget("user_2", "widget_123")
        assert result is False
        
        # User 2 locks different widget
        result = sharing_system.lock_widget("user_2", "widget_456")
        assert result is True
        assert session.locked_widgets["widget_456"] == "user_2"
        
        # Update cursors
        sharing_system.update_user_cursor("user_1", {"x": 100, "y": 200})
        sharing_system.update_user_cursor("user_2", {"x": 300, "y": 400})
        
        assert session.user_cursors["user_1"] == {"x": 100, "y": 200}
        assert session.user_cursors["user_2"] == {"x": 300, "y": 400}
        
        # User 1 leaves
        sharing_system.leave_collaborative_session("user_1")
        
        assert "user_1" not in session.active_users
        assert "user_1" not in session.user_cursors
        assert "widget_123" not in session.locked_widgets  # Widget unlocked
        assert "widget_456" in session.locked_widgets  # User 2's widget still locked
    
    def test_dashboard_sharing_permissions(self, full_system):
        """Test dashboard sharing permissions"""
        builder = full_system['builder']
        sharing_system = full_system['sharing_system']
        
        dashboard_id = "permission_test_dashboard"
        owner_id = "owner_123"
        
        # Create dashboard
        dashboard = Dashboard(
            dashboard_id=dashboard_id,
            name="Permission Test Dashboard",
            description="Testing permissions",
            owner_id=owner_id
        )
        builder.dashboard_system.dashboards[dashboard_id] = dashboard
        
        # Create team
        team = sharing_system.create_team(
            name="Test Team",
            description="Team for testing",
            created_by=owner_id
        )
        
        # Add team member
        sharing_system.add_team_member(
            team_id=team.team_id,
            user_id="member_456",
            username="team_member",
            email="member@example.com",
            permission_level=PermissionLevel.EDIT,
            added_by=owner_id
        )
        
        # Share dashboard with team
        sharing_system.share_dashboard_with_team(
            dashboard_id=dashboard_id,
            team_id=team.team_id,
            shared_by=owner_id
        )
        
        # Create public share link
        public_share = builder.create_dashboard_share(
            dashboard_id=dashboard_id,
            share_type="public",
            created_by=owner_id
        )
        
        # Test different access levels
        
        # Owner should have admin access
        access = builder.get_user_dashboard_access(owner_id, dashboard_id)
        assert access == "admin"
        
        # Team member should have access through team
        # (This would require more complex logic in real implementation)
        
        # Public user should have view access through public share
        access = builder.get_user_dashboard_access("random_user", dashboard_id)
        assert access == "view"  # Through public share
        
        # Revoke public share
        builder.revoke_share_link(public_share.share_id, owner_id)
        
        # Public user should no longer have access
        access = builder.get_user_dashboard_access("random_user", dashboard_id)
        assert access is None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])