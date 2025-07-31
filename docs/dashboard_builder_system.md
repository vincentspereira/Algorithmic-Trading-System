# Dashboard Builder System

## Overview

The Dashboard Builder System provides a comprehensive, drag-and-drop dashboard creation and management platform for the Nautilus Trader Engine. It enables users to create personalized dashboards with widgets, share them with teams, collaborate in real-time, and customize layouts to meet specific trading and analytics needs.

## Features

### Core Capabilities

1. **Drag-and-Drop Builder**
   - Visual dashboard creation interface
   - Widget palette with pre-built components
   - Grid-based layout system with snap-to-grid
   - Real-time preview and editing

2. **Widget-Based Architecture**
   - Extensive widget library (charts, tables, metrics, etc.)
   - Customizable widget properties and styling
   - Data source configuration
   - Responsive widget sizing and positioning

3. **Dashboard Sharing**
   - Public, private, and team-based sharing
   - Granular permission controls (view, comment, edit, admin)
   - Secure share links with expiration and access limits
   - Password protection and domain restrictions

4. **Real-Time Collaboration**
   - Multi-user editing sessions
   - Live cursor tracking and user presence
   - Widget locking during editing
   - Collaborative comments and annotations

5. **Personalization**
   - User preferences and settings
   - Custom themes and styling
   - Favorite widgets and templates
   - Dashboard templates and presets

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Dashboard Builder System                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Dashboard       │  │ Widget          │  │ Sharing         │  │
│  │ Builder         │  │ Templates       │  │ System          │  │
│  │                 │  │                 │  │                 │  │
│  │ - Drag & Drop   │  │ - Trading       │  │ - Share Links   │  │
│  │ - Layout Mgmt   │  │ - Analytics     │  │ - Teams         │  │
│  │ - Properties    │  │ - Risk          │  │ - Permissions   │  │
│  │ - Export/Import │  │ - Market Data   │  │ - Collaboration │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Frontend        │  │ User            │  │ Analytics       │  │
│  │ Components      │  │ Preferences     │  │ & Reporting     │  │
│  │                 │  │                 │  │                 │  │
│  │ - HTML/CSS/JS   │  │ - Themes        │  │ - Usage Stats   │  │
│  │ - GridStack     │  │ - Settings      │  │ - Performance   │  │
│  │ - Bootstrap     │  │ - Favorites     │  │ - Sharing Metrics│  │
│  │ - Socket.IO     │  │ - Recent Items  │  │ - User Behavior │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Dashboard Creation**
   ```
   User → Builder Interface → Widget Selection → Layout Design → Save
   ```

2. **Real-Time Collaboration**
   ```
   User Action → WebSocket → Server → Broadcast → Other Users
   ```

3. **Sharing Workflow**
   ```
   Create Share → Generate Link → Set Permissions → Distribute → Access Control
   ```

## Implementation

### Basic Usage

```python
from nautilus_trader_engine.visualization.dashboard_builder import create_dashboard_builder
from nautilus_trader_engine.visualization.customizable_dashboard import create_dashboard_system

# Create dashboard system
dashboard_system = create_dashboard_system()

# Create dashboard builder
builder = create_dashboard_builder(dashboard_system)

# Run the system
dashboard_system.run(debug=False)
```

### Widget Templates

```python
from nautilus_trader_engine.visualization.dashboard_builder import WidgetTemplate, WidgetCategory

# Create custom widget template
custom_template = WidgetTemplate(
    template_id="custom_metric",
    name="Custom Metric",
    description="Custom trading metric widget",
    category=WidgetCategory.TRADING,
    widget_type=WidgetType.METRIC,
    default_config=WidgetConfig(
        widget_id="custom_metric",
        widget_type=WidgetType.METRIC,
        title="Custom Metric",
        data_source="custom_data",
        position={"x": 0, "y": 0, "w": 4, "h": 3},
        parameters={"calculation": "custom_formula"}
    ),
    tags=["custom", "metric", "trading"]
)

# Add to builder
builder.widget_templates[custom_template.template_id] = custom_template
```

### Dashboard Sharing

```python
from nautilus_trader_engine.visualization.dashboard_sharing import create_sharing_system

# Create sharing system
sharing_system = create_sharing_system()

# Create share link
share_link = sharing_system.create_share_link(
    dashboard_id="dashboard_123",
    share_type=ShareType.PUBLIC,
    permission_level=PermissionLevel.VIEW,
    created_by="user_123",
    expires_hours=24,
    password="secure123"
)

print(f"Share URL: /shared/{share_link.link_id}")
```

### Team Collaboration

```python
# Create team
team = sharing_system.create_team(
    name="Trading Team Alpha",
    description="Primary trading team",
    created_by="team_lead_123"
)

# Add team members
sharing_system.add_team_member(
    team_id=team.team_id,
    user_id="trader_456",
    username="jane_trader",
    email="jane@company.com",
    permission_level=PermissionLevel.EDIT,
    added_by="team_lead_123"
)

# Share dashboard with team
sharing_system.share_dashboard_with_team(
    dashboard_id="dashboard_123",
    team_id=team.team_id,
    shared_by="team_lead_123"
)
```

### Real-Time Collaboration

```python
# Start collaborative session
session_id = sharing_system.start_collaborative_session(
    dashboard_id="dashboard_123",
    user_id="user_123"
)

# Lock widget for editing
sharing_system.lock_widget("user_123", "widget_456")

# Update cursor position
sharing_system.update_user_cursor("user_123", {"x": 100, "y": 200})

# Add comment
comment = sharing_system.add_comment(
    dashboard_id="dashboard_123",
    user_id="user_123",
    username="trader_john",
    content="This chart shows unusual activity",
    widget_id="widget_456",
    position={"x": 150, "y": 250}
)
```

## API Reference

### Dashboard Builder API

#### Create Widget from Template
```http
POST /api/builder/create_widget
Content-Type: application/json

{
    "template_id": "portfolio_summary",
    "dashboard_id": "dashboard_123",
    "position": {"x": 0, "y": 0, "w": 4, "h": 3}
}
```

#### Update Widget
```http
PUT /api/builder/update_widget
Content-Type: application/json

{
    "dashboard_id": "dashboard_123",
    "widget_id": "widget_456",
    "updates": {
        "title": "Updated Widget Title",
        "position": {"x": 2, "y": 1, "w": 6, "h": 4}
    }
}
```

#### Save Layout
```http
POST /api/builder/save_layout
Content-Type: application/json

{
    "dashboard_id": "dashboard_123",
    "layout": [
        {
            "widget_id": "widget_456",
            "position": {"x": 0, "y": 0, "w": 4, "h": 3}
        }
    ]
}
```

#### Get Widget Templates
```http
GET /api/builder/widget_templates?category=trading
```

Response:
```json
[
    {
        "template_id": "portfolio_summary",
        "name": "Portfolio Summary",
        "description": "Portfolio value and performance",
        "category": "trading",
        "widget_type": "metric",
        "tags": ["portfolio", "trading", "summary"]
    }
]
```

### Sharing API

#### Create Share Link
```http
POST /api/sharing/create_link
Content-Type: application/json

{
    "dashboard_id": "dashboard_123",
    "share_type": "public",
    "permission_level": "view",
    "expires_hours": 24,
    "password": "secure123"
}
```

Response:
```json
{
    "success": true,
    "share_link": {
        "link_id": "abc123def456",
        "share_url": "/shared/abc123def456",
        "expires_at": "2024-01-16T10:30:00Z"
    }
}
```

#### Validate Share Link
```http
POST /api/sharing/validate_link
Content-Type: application/json

{
    "link_id": "abc123def456",
    "password": "secure123"
}
```

### WebSocket Events

#### Join Builder Session
```javascript
socket.emit('join_builder', {
    dashboard_id: 'dashboard_123',
    user_id: 'user_123'
});
```

#### Widget Drag Events
```javascript
// Drag start
socket.emit('widget_drag_start', {
    dashboard_id: 'dashboard_123',
    widget_id: 'widget_456',
    user_id: 'user_123'
});

// Drag end
socket.emit('widget_drag_end', {
    dashboard_id: 'dashboard_123',
    widget_id: 'widget_456',
    position: {x: 2, y: 1, w: 4, h: 3}
});
```

#### Collaborative Editing
```javascript
socket.emit('collaborative_edit', {
    dashboard_id: 'dashboard_123',
    edit_type: 'widget_updated',
    edit_data: {
        widget_id: 'widget_456',
        property: 'title',
        value: 'New Title'
    },
    user_id: 'user_123'
});
```

## Widget Types and Templates

### Available Widget Categories

1. **Trading Widgets**
   - Portfolio Summary
   - Positions Table
   - Order Entry Form
   - Trade History
   - Account Balance

2. **Analytics Widgets**
   - P&L Chart
   - Performance Metrics
   - Risk Analytics
   - Correlation Matrix
   - Volatility Surface

3. **Market Data Widgets**
   - Watchlist
   - Order Book
   - Time & Sales
   - Market News
   - Economic Calendar

4. **Risk Widgets**
   - VaR Dashboard
   - Exposure Analysis
   - Stress Test Results
   - Risk Limits Monitor
   - Concentration Report

5. **Compliance Widgets**
   - Compliance Status
   - Violation Alerts
   - Audit Trail
   - Regulatory Reports
   - Trade Surveillance

### Widget Configuration

Each widget supports the following configuration options:

```javascript
{
    widget_id: "unique_widget_id",
    widget_type: "chart|table|metric|gauge|alert|news|calendar|watchlist",
    title: "Widget Title",
    data_source: "data_source_name",
    position: {
        x: 0,      // Grid column position
        y: 0,      // Grid row position
        w: 4,      // Width in grid units
        h: 3       // Height in grid units
    },
    refresh_interval: 30,  // Seconds
    parameters: {
        // Widget-specific parameters
        symbol: "AAPL",
        timeframe: "1D",
        indicators: ["SMA", "RSI"]
    },
    styling: {
        // Visual styling options
        background_color: "#ffffff",
        border_color: "#dee2e6",
        text_color: "#212529",
        chart_colors: ["#007bff", "#28a745", "#dc3545"]
    },
    is_visible: true,
    is_resizable: true,
    is_draggable: true,
    min_size: {w: 2, h: 2},
    max_size: {w: 12, h: 8}
}
```

## Frontend Components

### HTML Structure

The dashboard builder uses a three-panel layout:

```html
<div class="dashboard-builder">
    <!-- Header with save, share, preview buttons -->
    <div class="builder-header">...</div>
    
    <!-- Toolbar with grid settings and theme selection -->
    <div class="builder-toolbar">...</div>
    
    <!-- Main content area -->
    <div class="builder-content">
        <!-- Widget palette -->
        <div class="widget-palette">...</div>
        
        <!-- Dashboard canvas with GridStack -->
        <div class="dashboard-canvas">
            <div class="grid-stack" id="dashboard-grid"></div>
        </div>
        
        <!-- Properties panel -->
        <div class="properties-panel">...</div>
    </div>
</div>
```

### CSS Classes

Key CSS classes for styling:

- `.dashboard-builder` - Main container
- `.widget-palette` - Left sidebar with widget templates
- `.dashboard-canvas` - Center area with grid
- `.properties-panel` - Right sidebar with settings
- `.grid-stack-item` - Individual widgets
- `.widget-template` - Draggable widget templates
- `.collaboration-bar` - Real-time collaboration indicators

### JavaScript API

The frontend provides a JavaScript API for programmatic control:

```javascript
// Initialize builder
const builder = new DashboardBuilder();

// Add widget programmatically
builder.addWidgetFromTemplate('portfolio_summary', {x: 0, y: 0});

// Select widget
builder.selectWidget('widget_123');

// Update widget property
builder.updateWidgetProperty('title', 'New Title');

// Save dashboard
builder.saveDashboard();

// Export dashboard
const exportData = builder.serializeDashboard();
```

## Customization

### Custom Widget Templates

Create custom widget templates by extending the base template:

```python
class CustomWidgetTemplate(WidgetTemplate):
    def __init__(self):
        super().__init__(
            template_id="custom_indicator",
            name="Custom Technical Indicator",
            description="Custom technical analysis widget",
            category=WidgetCategory.ANALYTICS,
            widget_type=WidgetType.CHART,
            default_config=WidgetConfig(
                widget_id="custom_indicator",
                widget_type=WidgetType.CHART,
                title="Custom Indicator",
                data_source="technical_analysis",
                parameters={
                    "indicator_type": "custom",
                    "period": 14,
                    "calculation": "custom_formula"
                }
            )
        )
```

### Custom Themes

Define custom themes for dashboard styling:

```python
custom_theme = DashboardTheme(
    theme_id="corporate_blue",
    theme_type=ThemeType.CUSTOM,
    name="Corporate Blue",
    colors={
        "primary": "#1e3a8a",
        "secondary": "#64748b",
        "success": "#059669",
        "danger": "#dc2626",
        "warning": "#d97706",
        "info": "#0284c7",
        "background": "#f8fafc",
        "surface": "#ffffff",
        "text": "#1e293b"
    },
    fonts={
        "primary": "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
        "monospace": "'JetBrains Mono', 'Fira Code', monospace"
    },
    custom_css="""
        .grid-stack-item {
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        .widget-header {
            background: linear-gradient(135deg, #1e3a8a, #3b82f6);
            color: white;
        }
    """
)
```

### Data Source Integration

Integrate custom data sources for widgets:

```python
class CustomDataProvider(WidgetDataProvider):
    def __init__(self):
        super().__init__("custom_data")
    
    async def get_widget_data(self, widget_config: WidgetConfig) -> Dict[str, Any]:
        # Implement custom data retrieval logic
        if widget_config.data_source == "custom_metrics":
            return await self._get_custom_metrics(widget_config.parameters)
        
        return {}
    
    async def _get_custom_metrics(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        # Custom data processing
        return {
            "value": 12345.67,
            "formatted_value": "$12,345.67",
            "change": 234.56,
            "change_percent": 1.95,
            "status": "positive",
            "trend": "up"
        }

# Register custom data provider
dashboard_system.data_providers["custom_data"] = CustomDataProvider()
```

## Performance Optimization

### Client-Side Optimization

1. **Lazy Loading**
   - Load widget data on demand
   - Implement virtual scrolling for large datasets
   - Use intersection observer for viewport-based loading

2. **Caching**
   - Cache widget configurations locally
   - Implement service worker for offline functionality
   - Use browser storage for user preferences

3. **Rendering Optimization**
   - Debounce resize and drag events
   - Use requestAnimationFrame for smooth animations
   - Implement efficient DOM updates

### Server-Side Optimization

1. **Data Caching**
   - Cache frequently accessed dashboard configurations
   - Implement Redis for session storage
   - Use CDN for static assets

2. **WebSocket Optimization**
   - Batch collaborative events
   - Implement connection pooling
   - Use message compression

3. **Database Optimization**
   - Index dashboard and widget queries
   - Implement database connection pooling
   - Use read replicas for analytics

## Security Considerations

### Access Control

1. **Authentication**
   - Integrate with existing authentication system
   - Support SSO and multi-factor authentication
   - Implement session management

2. **Authorization**
   - Role-based access control (RBAC)
   - Resource-level permissions
   - API rate limiting

3. **Data Protection**
   - Encrypt sensitive dashboard data
   - Sanitize user inputs
   - Implement CSRF protection

### Share Link Security

1. **Secure Generation**
   - Use cryptographically secure random tokens
   - Implement token expiration
   - Support password protection

2. **Access Monitoring**
   - Log share link access attempts
   - Monitor for suspicious activity
   - Implement access count limits

## Deployment

### Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Start development server
python -m nautilus_trader_engine.visualization.customizable_dashboard

# Access builder at http://localhost:5002/builder
```

### Production Deployment

```yaml
# docker-compose.yml
version: '3.8'
services:
  dashboard-system:
    build: .
    ports:
      - "5002:5002"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://user:pass@db:5432/dashboards
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:13
    environment:
      POSTGRES_DB: dashboards
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:6-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dashboard-builder
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dashboard-builder
  template:
    metadata:
      labels:
        app: dashboard-builder
    spec:
      containers:
      - name: dashboard-builder
        image: nautilus-trader/dashboard-builder:latest
        ports:
        - containerPort: 5002
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: dashboard-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: dashboard-secrets
              key: redis-url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

## Monitoring and Analytics

### Usage Metrics

Track key metrics for dashboard usage:

- Dashboard creation and modification rates
- Widget usage patterns
- Sharing and collaboration activity
- Performance metrics (load times, error rates)
- User engagement (session duration, feature usage)

### Performance Monitoring

```python
# Example monitoring integration
import logging
from prometheus_client import Counter, Histogram, Gauge

# Metrics
dashboard_creations = Counter('dashboard_creations_total', 'Total dashboard creations')
widget_additions = Counter('widget_additions_total', 'Total widget additions', ['widget_type'])
collaboration_sessions = Gauge('collaboration_sessions_active', 'Active collaboration sessions')
dashboard_load_time = Histogram('dashboard_load_seconds', 'Dashboard load time')

# Usage in code
dashboard_creations.inc()
widget_additions.labels(widget_type='chart').inc()
collaboration_sessions.set(len(sharing_system.collaborative_sessions))
```

### Error Tracking

Implement comprehensive error tracking:

```python
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[FlaskIntegration()],
    traces_sample_rate=1.0
)
```

## Troubleshooting

### Common Issues

1. **Widget Not Loading**
   - Check data source configuration
   - Verify API endpoints are accessible
   - Review browser console for JavaScript errors

2. **Drag and Drop Not Working**
   - Ensure GridStack is properly initialized
   - Check for CSS conflicts
   - Verify touch events on mobile devices

3. **Collaboration Issues**
   - Check WebSocket connection status
   - Verify user authentication
   - Review server logs for connection errors

4. **Performance Problems**
   - Monitor widget refresh intervals
   - Check for memory leaks in JavaScript
   - Optimize database queries

### Debug Mode

Enable debug mode for detailed logging:

```python
dashboard_system = create_dashboard_system()
dashboard_system.run(debug=True)
```

### Logging Configuration

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dashboard_builder.log'),
        logging.StreamHandler()
    ]
)
```

## Future Enhancements

### Planned Features

1. **Advanced Widgets**
   - 3D visualizations
   - Interactive maps
   - Video streaming widgets
   - AI-powered insights

2. **Enhanced Collaboration**
   - Voice/video chat integration
   - Screen sharing
   - Collaborative annotations
   - Version control for dashboards

3. **Mobile Optimization**
   - Native mobile apps
   - Touch gesture improvements
   - Offline synchronization
   - Push notifications

4. **AI Integration**
   - Automated dashboard generation
   - Smart widget recommendations
   - Anomaly detection in dashboards
   - Natural language queries

5. **Enterprise Features**
   - Advanced audit logging
   - Compliance reporting
   - Enterprise SSO integration
   - White-label customization

## Support and Documentation

### Getting Help

- **Documentation**: Comprehensive guides and API reference
- **Examples**: Sample dashboards and widget implementations
- **Community**: Forums and discussion groups
- **Support**: Professional support options

### Contributing

Contributions are welcome! Please see the contributing guidelines for:

- Code style and standards
- Testing requirements
- Documentation updates
- Feature request process

### License

The Dashboard Builder System is part of the Nautilus Trader Engine and follows the same licensing terms.