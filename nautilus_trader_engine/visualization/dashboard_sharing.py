"""
Dashboard Sharing System
Provides comprehensive dashboard sharing capabilities including public/private sharing,
team collaboration, permission management, and real-time collaborative editing.
"""
import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
import hashlib
import secrets

try:
    from flask import Flask, render_template, jsonify, request, session, redirect, url_for
    from flask_socketio import SocketIO, emit, join_room, leave_room
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

class ShareType(Enum):
    """Dashboard share types"""
    PUBLIC = "public"           # Anyone with link can view
    PRIVATE = "private"         # Only specific users
    TEAM = "team"              # Team members only
    ORGANIZATION = "organization"  # Organization members only

class PermissionLevel(Enum):
    """Permission levels for dashboard access"""
    VIEW = "view"              # Can only view dashboard
    COMMENT = "comment"        # Can view and add comments
    EDIT = "edit"             # Can edit dashboard
    ADMIN = "admin"           # Full control including sharing

class CollaborationEvent(Enum):
    """Real-time collaboration events"""
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    WIDGET_SELECTED = "widget_selected"
    WIDGET_EDITING = "widget_editing"
    WIDGET_MOVED = "widget_moved"
    WIDGET_RESIZED = "widget_resized"
    COMMENT_ADDED = "comment_added"
    CURSOR_MOVED = "cursor_moved"

@dataclass
class ShareLink:
    """Dashboard share link"""
    link_id: str
    dashboard_id: str
    share_type: ShareType
    permission_level: PermissionLevel
    created_by: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    access_count: int = 0
    max_access_count: Optional[int] = None
    password_hash: Optional[str] = None
    is_active: bool = True
    allowed_domains: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TeamMember:
    """Team member information"""
    user_id: str
    username: str
    email: str
    role: str
    permission_level: PermissionLevel
    joined_at: datetime
    last_active: Optional[datetime] = None
    is_active: bool = True

@dataclass
class Team:
    """Team for dashboard sharing"""
    team_id: str
    name: str
    description: str
    created_by: str
    created_at: datetime
    members: List[TeamMember] = field(default_factory=list)
    shared_dashboards: List[str] = field(default_factory=list)
    is_active: bool = True

@dataclass
class Comment:
    """Dashboard comment"""
    comment_id: str
    dashboard_id: str
    widget_id: Optional[str]  # None for dashboard-level comments
    user_id: str
    username: str
    content: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    parent_comment_id: Optional[str] = None  # For replies
    is_resolved: bool = False
    position: Optional[Dict[str, float]] = None  # For positioned comments

@dataclass
class CollaborativeSession:
    """Real-time collaborative editing session"""
    session_id: str
    dashboard_id: str
    active_users: Set[str] = field(default_factory=set)
    user_cursors: Dict[str, Dict[str, float]] = field(default_factory=dict)
    locked_widgets: Dict[str, str] = field(default_factory=dict)  # widget_id -> user_id
    started_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)

class DashboardSharingSystem:
    """Advanced dashboard sharing and collaboration system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Storage
        self.share_links: Dict[str, ShareLink] = {}
        self.teams: Dict[str, Team] = {}
        self.comments: Dict[str, List[Comment]] = {}  # dashboard_id -> comments
        self.collaborative_sessions: Dict[str, CollaborativeSession] = {}
        
        # Real-time collaboration
        self.active_sessions: Dict[str, Set[str]] = {}  # dashboard_id -> user_ids
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id
    
    def create_share_link(self, dashboard_id: str, share_type: ShareType,
                         permission_level: PermissionLevel, created_by: str,
                         expires_hours: Optional[int] = None,
                         max_access_count: Optional[int] = None,
                         password: Optional[str] = None,
                         allowed_domains: List[str] = None) -> ShareLink:
        """Create a new share link"""
        link_id = secrets.token_urlsafe(32)
        
        expires_at = None
        if expires_hours:
            expires_at = datetime.now() + timedelta(hours=expires_hours)
        
        password_hash = None
        if password:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        share_link = ShareLink(
            link_id=link_id,
            dashboard_id=dashboard_id,
            share_type=share_type,
            permission_level=permission_level,
            created_by=created_by,
            created_at=datetime.now(),
            expires_at=expires_at,
            max_access_count=max_access_count,
            password_hash=password_hash,
            allowed_domains=allowed_domains or []
        )
        
        self.share_links[link_id] = share_link
        
        self.logger.info(f"Created share link {link_id} for dashboard {dashboard_id}")
        return share_link
    
    def validate_share_link(self, link_id: str, user_id: str,
                          password: Optional[str] = None,
                          user_domain: Optional[str] = None) -> Optional[ShareLink]:
        """Validate share link access"""
        share_link = self.share_links.get(link_id)
        if not share_link or not share_link.is_active:
            return None
        
        # Check expiration
        if share_link.expires_at and share_link.expires_at < datetime.now():
            return None
        
        # Check access count limit
        if (share_link.max_access_count and 
            share_link.access_count >= share_link.max_access_count):
            return None
        
        # Check password
        if share_link.password_hash:
            if not password:
                return None
            if hashlib.sha256(password.encode()).hexdigest() != share_link.password_hash:
                return None
        
        # Check domain restrictions
        if share_link.allowed_domains and user_domain:
            if user_domain not in share_link.allowed_domains:
                return None
        
        # Increment access count
        share_link.access_count += 1
        
        return share_link
    
    def revoke_share_link(self, link_id: str, user_id: str) -> bool:
        """Revoke a share link"""
        share_link = self.share_links.get(link_id)
        if not share_link:
            return False
        
        # Check if user has permission to revoke
        if share_link.created_by != user_id:
            return False
        
        share_link.is_active = False
        self.logger.info(f"Revoked share link {link_id}")
        return True
    
    def create_team(self, name: str, description: str, created_by: str) -> Team:
        """Create a new team"""
        team_id = str(uuid.uuid4())
        
        team = Team(
            team_id=team_id,
            name=name,
            description=description,
            created_by=created_by,
            created_at=datetime.now()
        )
        
        # Add creator as admin
        creator_member = TeamMember(
            user_id=created_by,
            username=f"user_{created_by}",  # In real implementation, get from user service
            email=f"{created_by}@example.com",
            role="admin",
            permission_level=PermissionLevel.ADMIN,
            joined_at=datetime.now()
        )
        
        team.members.append(creator_member)
        self.teams[team_id] = team
        
        self.logger.info(f"Created team {team_id}: {name}")
        return team
    
    def add_team_member(self, team_id: str, user_id: str, username: str,
                       email: str, permission_level: PermissionLevel,
                       added_by: str) -> bool:
        """Add member to team"""
        team = self.teams.get(team_id)
        if not team:
            return False
        
        # Check if user adding has admin permission
        admin_member = next((m for m in team.members 
                           if m.user_id == added_by and 
                           m.permission_level == PermissionLevel.ADMIN), None)
        if not admin_member:
            return False
        
        # Check if user is already a member
        existing_member = next((m for m in team.members if m.user_id == user_id), None)
        if existing_member:
            return False
        
        member = TeamMember(
            user_id=user_id,
            username=username,
            email=email,
            role="member",
            permission_level=permission_level,
            joined_at=datetime.now()
        )
        
        team.members.append(member)
        self.logger.info(f"Added user {user_id} to team {team_id}")
        return True
    
    def share_dashboard_with_team(self, dashboard_id: str, team_id: str,
                                 shared_by: str) -> bool:
        """Share dashboard with team"""
        team = self.teams.get(team_id)
        if not team:
            return False
        
        # Check if user is team member with appropriate permissions
        member = next((m for m in team.members 
                      if m.user_id == shared_by and 
                      m.permission_level in [PermissionLevel.ADMIN, PermissionLevel.EDIT]), None)
        if not member:
            return False
        
        if dashboard_id not in team.shared_dashboards:
            team.shared_dashboards.append(dashboard_id)
            self.logger.info(f"Shared dashboard {dashboard_id} with team {team_id}")
        
        return True
    
    def add_comment(self, dashboard_id: str, user_id: str, username: str,
                   content: str, widget_id: Optional[str] = None,
                   parent_comment_id: Optional[str] = None,
                   position: Optional[Dict[str, float]] = None) -> Comment:
        """Add comment to dashboard"""
        comment = Comment(
            comment_id=str(uuid.uuid4()),
            dashboard_id=dashboard_id,
            widget_id=widget_id,
            user_id=user_id,
            username=username,
            content=content,
            created_at=datetime.now(),
            parent_comment_id=parent_comment_id,
            position=position
        )
        
        if dashboard_id not in self.comments:
            self.comments[dashboard_id] = []
        
        self.comments[dashboard_id].append(comment)
        
        self.logger.info(f"Added comment {comment.comment_id} to dashboard {dashboard_id}")
        return comment
    
    def resolve_comment(self, comment_id: str, user_id: str) -> bool:
        """Resolve a comment"""
        for dashboard_comments in self.comments.values():
            for comment in dashboard_comments:
                if comment.comment_id == comment_id:
                    comment.is_resolved = True
                    comment.updated_at = datetime.now()
                    self.logger.info(f"Resolved comment {comment_id}")
                    return True
        return False
    
    def get_dashboard_comments(self, dashboard_id: str) -> List[Comment]:
        """Get all comments for a dashboard"""
        return self.comments.get(dashboard_id, [])
    
    def start_collaborative_session(self, dashboard_id: str, user_id: str) -> str:
        """Start or join collaborative editing session"""
        session_id = f"collab_{dashboard_id}"
        
        if session_id not in self.collaborative_sessions:
            self.collaborative_sessions[session_id] = CollaborativeSession(
                session_id=session_id,
                dashboard_id=dashboard_id
            )
        
        session = self.collaborative_sessions[session_id]
        session.active_users.add(user_id)
        session.last_activity = datetime.now()
        
        self.user_sessions[user_id] = session_id
        
        if dashboard_id not in self.active_sessions:
            self.active_sessions[dashboard_id] = set()
        self.active_sessions[dashboard_id].add(user_id)
        
        self.logger.info(f"User {user_id} joined collaborative session for dashboard {dashboard_id}")
        return session_id
    
    def leave_collaborative_session(self, user_id: str) -> Optional[str]:
        """Leave collaborative editing session"""
        session_id = self.user_sessions.get(user_id)
        if not session_id:
            return None
        
        session = self.collaborative_sessions.get(session_id)
        if session:
            session.active_users.discard(user_id)
            session.user_cursors.pop(user_id, None)
            
            # Release any locked widgets
            widgets_to_unlock = [widget_id for widget_id, locked_user 
                               in session.locked_widgets.items() 
                               if locked_user == user_id]
            for widget_id in widgets_to_unlock:
                del session.locked_widgets[widget_id]
            
            dashboard_id = session.dashboard_id
            if dashboard_id in self.active_sessions:
                self.active_sessions[dashboard_id].discard(user_id)
        
        del self.user_sessions[user_id]
        
        self.logger.info(f"User {user_id} left collaborative session {session_id}")
        return session_id
    
    def lock_widget(self, user_id: str, widget_id: str) -> bool:
        """Lock widget for editing"""
        session_id = self.user_sessions.get(user_id)
        if not session_id:
            return False
        
        session = self.collaborative_sessions.get(session_id)
        if not session:
            return False
        
        # Check if widget is already locked
        if widget_id in session.locked_widgets:
            return session.locked_widgets[widget_id] == user_id
        
        session.locked_widgets[widget_id] = user_id
        session.last_activity = datetime.now()
        
        return True
    
    def unlock_widget(self, user_id: str, widget_id: str) -> bool:
        """Unlock widget"""
        session_id = self.user_sessions.get(user_id)
        if not session_id:
            return False
        
        session = self.collaborative_sessions.get(session_id)
        if not session:
            return False
        
        if (widget_id in session.locked_widgets and 
            session.locked_widgets[widget_id] == user_id):
            del session.locked_widgets[widget_id]
            session.last_activity = datetime.now()
            return True
        
        return False
    
    def update_user_cursor(self, user_id: str, cursor_position: Dict[str, float]) -> bool:
        """Update user cursor position"""
        session_id = self.user_sessions.get(user_id)
        if not session_id:
            return False
        
        session = self.collaborative_sessions.get(session_id)
        if not session:
            return False
        
        session.user_cursors[user_id] = cursor_position
        session.last_activity = datetime.now()
        
        return True
    
    def get_collaboration_state(self, dashboard_id: str) -> Dict[str, Any]:
        """Get current collaboration state"""
        session_id = f"collab_{dashboard_id}"
        session = self.collaborative_sessions.get(session_id)
        
        if not session:
            return {
                'active_users': [],
                'locked_widgets': {},
                'user_cursors': {}
            }
        
        return {
            'active_users': list(session.active_users),
            'locked_widgets': session.locked_widgets.copy(),
            'user_cursors': session.user_cursors.copy(),
            'last_activity': session.last_activity.isoformat()
        }
    
    def cleanup_inactive_sessions(self, timeout_minutes: int = 30):
        """Clean up inactive collaborative sessions"""
        cutoff_time = datetime.now() - timedelta(minutes=timeout_minutes)
        
        sessions_to_remove = []
        for session_id, session in self.collaborative_sessions.items():
            if session.last_activity < cutoff_time:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            session = self.collaborative_sessions[session_id]
            
            # Clean up user sessions
            for user_id in list(session.active_users):
                self.user_sessions.pop(user_id, None)
            
            # Clean up active sessions
            dashboard_id = session.dashboard_id
            if dashboard_id in self.active_sessions:
                for user_id in session.active_users:
                    self.active_sessions[dashboard_id].discard(user_id)
                
                if not self.active_sessions[dashboard_id]:
                    del self.active_sessions[dashboard_id]
            
            del self.collaborative_sessions[session_id]
            self.logger.info(f"Cleaned up inactive session {session_id}")
    
    def get_share_analytics(self, dashboard_id: str) -> Dict[str, Any]:
        """Get sharing analytics for dashboard"""
        # Find all share links for this dashboard
        dashboard_shares = [link for link in self.share_links.values() 
                          if link.dashboard_id == dashboard_id]
        
        total_access_count = sum(link.access_count for link in dashboard_shares)
        active_links = len([link for link in dashboard_shares if link.is_active])
        
        # Get team sharing info
        teams_with_access = [team for team in self.teams.values() 
                           if dashboard_id in team.shared_dashboards]
        
        # Get comment statistics
        dashboard_comments = self.comments.get(dashboard_id, [])
        resolved_comments = len([c for c in dashboard_comments if c.is_resolved])
        
        analytics = {
            'dashboard_id': dashboard_id,
            'total_shares': len(dashboard_shares),
            'active_shares': active_links,
            'total_access_count': total_access_count,
            'teams_with_access': len(teams_with_access),
            'total_comments': len(dashboard_comments),
            'resolved_comments': resolved_comments,
            'share_types': {
                share_type.value: len([link for link in dashboard_shares 
                                     if link.share_type == share_type])
                for share_type in ShareType
            },
            'permission_levels': {
                perm.value: len([link for link in dashboard_shares 
                               if link.permission_level == perm])
                for perm in PermissionLevel
            },
            'current_collaborative_users': len(self.active_sessions.get(dashboard_id, set())),
            'last_shared': max([link.created_at for link in dashboard_shares], 
                             default=datetime.min).isoformat() if dashboard_shares else None
        }
        
        return analytics
    
    def export_sharing_config(self, dashboard_id: str) -> Dict[str, Any]:
        """Export sharing configuration"""
        dashboard_shares = [asdict(link) for link in self.share_links.values() 
                          if link.dashboard_id == dashboard_id]
        
        teams_with_access = [asdict(team) for team in self.teams.values() 
                           if dashboard_id in team.shared_dashboards]
        
        dashboard_comments = [asdict(comment) for comment in self.comments.get(dashboard_id, [])]
        
        return {
            'dashboard_id': dashboard_id,
            'share_links': dashboard_shares,
            'teams': teams_with_access,
            'comments': dashboard_comments,
            'exported_at': datetime.now().isoformat()
        }

def create_sharing_system() -> DashboardSharingSystem:
    """Create dashboard sharing system"""
    return DashboardSharingSystem()

if __name__ == "__main__":
    # Example usage
    sharing_system = create_sharing_system()
    
    # Create a team
    team = sharing_system.create_team(
        name="Trading Team",
        description="Main trading team",
        created_by="user_123"
    )
    
    # Add team member
    sharing_system.add_team_member(
        team_id=team.team_id,
        user_id="user_456",
        username="trader_jane",
        email="jane@example.com",
        permission_level=PermissionLevel.EDIT,
        added_by="user_123"
    )
    
    # Create share link
    share_link = sharing_system.create_share_link(
        dashboard_id="dashboard_789",
        share_type=ShareType.TEAM,
        permission_level=PermissionLevel.VIEW,
        created_by="user_123",
        expires_hours=24
    )
    
    print(f"Created share link: {share_link.link_id}")
    print(f"Team created with {len(team.members)} members")
    
    # Start collaborative session
    session_id = sharing_system.start_collaborative_session("dashboard_789", "user_123")
    print(f"Started collaborative session: {session_id}")
    
    # Add comment
    comment = sharing_system.add_comment(
        dashboard_id="dashboard_789",
        user_id="user_123",
        username="trader_john",
        content="This chart needs updating",
        widget_id="widget_456"
    )
    
    print(f"Added comment: {comment.comment_id}")
    
    # Get analytics
    analytics = sharing_system.get_share_analytics("dashboard_789")
    print(f"Share analytics: {analytics}")