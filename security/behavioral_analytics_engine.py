#!/usr/bin/env python3
"""
Behavioral Analytics Engine
Advanced behavioral analysis for anomaly detection and user profiling
"""

import asyncio
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import pickle
import os
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import joblib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnomalyType(Enum):
    """Types of behavioral anomalies"""
    TIME_BASED = "TIME_BASED"
    LOCATION_BASED = "LOCATION_BASED"
    DEVICE_BASED = "DEVICE_BASED"
    ACTIVITY_BASED = "ACTIVITY_BASED"
    VOLUME_BASED = "VOLUME_BASED"
    PATTERN_BASED = "PATTERN_BASED"

class RiskLevel(Enum):
    """Risk levels for behavioral analysis"""
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"

@dataclass
class BehavioralEvent:
    """Individual behavioral event"""
    event_id: str
    user_id: str
    event_type: str
    timestamp: datetime
    location: Optional[str] = None
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    resource_accessed: Optional[str] = None
    action_performed: Optional[str] = None
    data_volume: int = 0
    duration: float = 0.0
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BehavioralPattern:
    """Identified behavioral pattern"""
    pattern_id: str
    user_id: str
    pattern_type: str
    description: str
    frequency: float
    confidence: float
    first_observed: datetime
    last_observed: datetime
    examples: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AnomalyDetection:
    """Anomaly detection result"""
    anomaly_id: str
    user_id: str
    anomaly_type: AnomalyType
    risk_level: RiskLevel
    confidence: float
    description: str
    detected_at: datetime
    triggering_events: List[str]
    baseline_behavior: Dict[str, Any]
    anomalous_behavior: Dict[str, Any]
    recommended_actions: List[str] = field(default_factory=list)

@dataclass
class UserBehavioralProfile:
    """Comprehensive user behavioral profile"""
    user_id: str
    created_at: datetime
    last_updated: datetime
    
    # Time-based patterns
    typical_login_hours: Dict[int, float]  # hour -> frequency
    typical_login_days: Dict[int, float]   # day_of_week -> frequency
    session_duration_stats: Dict[str, float]  # mean, std, min, max
    
    # Location patterns
    typical_locations: Dict[str, float]    # location -> frequency
    location_transitions: Dict[Tuple[str, str], float]  # (from, to) -> frequency
    
    # Device patterns
    typical_devices: Dict[str, float]      # device_id -> frequency
    device_switching_patterns: Dict[str, Any]
    
    # Activity patterns
    typical_resources: Dict[str, float]    # resource -> frequency
    typical_actions: Dict[str, float]      # action -> frequency
    activity_sequences: Dict[str, float]   # sequence -> frequency
    
    # Volume patterns
    data_access_volume: Dict[str, float]   # time_period -> volume
    request_rate_patterns: Dict[str, float]
    
    # Risk indicators
    risk_score: float = 0.0
    risk_factors: List[str] = field(default_factory=list)
    
    # ML model features
    feature_vector: Optional[np.ndarray] = None
    cluster_id: Optional[int] = None

class BehavioralAnalyticsEngine:
    """Advanced behavioral analytics engine"""
    
    def __init__(self, model_path: str = "models/behavioral"):
        self.model_path = model_path
        self.events: deque = deque(maxlen=100000)  # Store recent events
        self.user_profiles: Dict[str, UserBehavioralProfile] = {}
        self.behavioral_patterns: Dict[str, List[BehavioralPattern]] = defaultdict(list)
        self.anomaly_detections: List[AnomalyDetection] = []
        
        # ML models
        self.anomaly_detector = None
        self.clustering_model = None
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=10)
        
        # Configuration
        self.config = {
            'learning_period_days': 30,
            'anomaly_threshold': 0.7,
            'min_events_for_profile': 50,
            'pattern_confidence_threshold': 0.6,
            'model_retrain_interval_hours': 24,
            'feature_update_interval_minutes': 60
        }
        
        # Initialize models
        self._initialize_models()
        
        logger.info("Behavioral Analytics Engine initialized")
    
    def _initialize_models(self):
        """Initialize or load ML models"""
        try:
            # Create model directory if it doesn't exist
            os.makedirs(self.model_path, exist_ok=True)
            
            # Try to load existing models
            anomaly_model_path = os.path.join(self.model_path, 'anomaly_detector.joblib')
            clustering_model_path = os.path.join(self.model_path, 'clustering_model.joblib')
            scaler_path = os.path.join(self.model_path, 'scaler.joblib')
            pca_path = os.path.join(self.model_path, 'pca.joblib')
            
            if os.path.exists(anomaly_model_path):
                self.anomaly_detector = joblib.load(anomaly_model_path)
                logger.info("Loaded existing anomaly detection model")
            else:
                self.anomaly_detector = IsolationForest(
                    contamination=0.1,
                    random_state=42,
                    n_estimators=100
                )
                logger.info("Initialized new anomaly detection model")
            
            if os.path.exists(clustering_model_path):
                self.clustering_model = joblib.load(clustering_model_path)
                logger.info("Loaded existing clustering model")
            else:
                self.clustering_model = DBSCAN(eps=0.5, min_samples=5)
                logger.info("Initialized new clustering model")
            
            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)
                logger.info("Loaded existing scaler")
            
            if os.path.exists(pca_path):
                self.pca = joblib.load(pca_path)
                logger.info("Loaded existing PCA model")
                
        except Exception as e:
            logger.error(f"Error initializing models: {e}")
            # Initialize default models
            self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
            self.clustering_model = DBSCAN(eps=0.5, min_samples=5)
    
    def record_event(self, event: BehavioralEvent):
        """Record a behavioral event"""
        self.events.append(event)
        
        # Update user profile
        self._update_user_profile(event)
        
        # Check for real-time anomalies
        anomalies = self._detect_real_time_anomalies(event)
        if anomalies:
            self.anomaly_detections.extend(anomalies)
            
            # Log high-risk anomalies
            for anomaly in anomalies:
                if anomaly.risk_level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]:
                    logger.warning(f"High-risk anomaly detected: {anomaly.description}")
    
    def _update_user_profile(self, event: BehavioralEvent):
        """Update user behavioral profile with new event"""
        user_id = event.user_id
        
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserBehavioralProfile(
                user_id=user_id,
                created_at=datetime.now(),
                last_updated=datetime.now(),
                typical_login_hours=defaultdict(float),
                typical_login_days=defaultdict(float),
                session_duration_stats={},
                typical_locations=defaultdict(float),
                location_transitions=defaultdict(float),
                typical_devices=defaultdict(float),
                device_switching_patterns={},
                typical_resources=defaultdict(float),
                typical_actions=defaultdict(float),
                activity_sequences=defaultdict(float),
                data_access_volume=defaultdict(float),
                request_rate_patterns=defaultdict(float)
            )
        
        profile = self.user_profiles[user_id]
        
        # Update time-based patterns
        hour = event.timestamp.hour
        day_of_week = event.timestamp.weekday()
        profile.typical_login_hours[hour] += 1
        profile.typical_login_days[day_of_week] += 1
        
        # Update location patterns
        if event.location:
            profile.typical_locations[event.location] += 1
        
        # Update device patterns
        if event.device_id:
            profile.typical_devices[event.device_id] += 1
        
        # Update activity patterns
        if event.resource_accessed:
            profile.typical_resources[event.resource_accessed] += 1
        
        if event.action_performed:
            profile.typical_actions[event.action_performed] += 1
        
        # Update volume patterns
        if event.data_volume > 0:
            time_bucket = event.timestamp.strftime('%Y-%m-%d-%H')
            profile.data_access_volume[time_bucket] += event.data_volume
        
        profile.last_updated = datetime.now()
    
    def _detect_real_time_anomalies(self, event: BehavioralEvent) -> List[AnomalyDetection]:
        """Detect real-time anomalies for an event"""
        anomalies = []
        user_id = event.user_id
        
        if user_id not in self.user_profiles:
            return anomalies
        
        profile = self.user_profiles[user_id]
        
        # Time-based anomaly detection
        time_anomaly = self._detect_time_anomaly(event, profile)
        if time_anomaly:
            anomalies.append(time_anomaly)
        
        # Location-based anomaly detection
        location_anomaly = self._detect_location_anomaly(event, profile)
        if location_anomaly:
            anomalies.append(location_anomaly)
        
        # Device-based anomaly detection
        device_anomaly = self._detect_device_anomaly(event, profile)
        if device_anomaly:
            anomalies.append(device_anomaly)
        
        # Volume-based anomaly detection
        volume_anomaly = self._detect_volume_anomaly(event, profile)
        if volume_anomaly:
            anomalies.append(volume_anomaly)
        
        return anomalies
    
    def _detect_time_anomaly(self, event: BehavioralEvent, profile: UserBehavioralProfile) -> Optional[AnomalyDetection]:
        """Detect time-based anomalies"""
        hour = event.timestamp.hour
        day_of_week = event.timestamp.weekday()
        
        # Calculate typical activity for this hour and day
        total_hour_events = sum(profile.typical_login_hours.values())
        total_day_events = sum(profile.typical_login_days.values())
        
        if total_hour_events < 10:  # Not enough data
            return None
        
        hour_frequency = profile.typical_login_hours.get(hour, 0) / total_hour_events
        day_frequency = profile.typical_login_days.get(day_of_week, 0) / total_day_events
        
        # Check if this is an unusual time
        if hour_frequency < 0.05 and day_frequency < 0.1:  # Very rare time
            confidence = 1.0 - (hour_frequency + day_frequency)
            risk_level = RiskLevel.HIGH if confidence > 0.8 else RiskLevel.MEDIUM
            
            return AnomalyDetection(
                anomaly_id=f"time_anomaly_{event.event_id}",
                user_id=event.user_id,
                anomaly_type=AnomalyType.TIME_BASED,
                risk_level=risk_level,
                confidence=confidence,
                description=f"Unusual login time: {hour}:00 on {['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][day_of_week]}",
                detected_at=datetime.now(),
                triggering_events=[event.event_id],
                baseline_behavior={
                    'typical_hours': dict(profile.typical_login_hours),
                    'typical_days': dict(profile.typical_login_days)
                },
                anomalous_behavior={
                    'current_hour': hour,
                    'current_day': day_of_week,
                    'hour_frequency': hour_frequency,
                    'day_frequency': day_frequency
                },
                recommended_actions=['require_additional_authentication', 'monitor_session_closely']
            )
        
        return None
    
    def _detect_location_anomaly(self, event: BehavioralEvent, profile: UserBehavioralProfile) -> Optional[AnomalyDetection]:
        """Detect location-based anomalies"""
        if not event.location:
            return None
        
        total_location_events = sum(profile.typical_locations.values())
        if total_location_events < 5:  # Not enough data
            return None
        
        location_frequency = profile.typical_locations.get(event.location, 0) / total_location_events
        
        # Check if this is a new or very rare location
        if location_frequency < 0.1:  # Less than 10% of typical activity
            confidence = 1.0 - location_frequency
            risk_level = RiskLevel.HIGH if event.location not in profile.typical_locations else RiskLevel.MEDIUM
            
            return AnomalyDetection(
                anomaly_id=f"location_anomaly_{event.event_id}",
                user_id=event.user_id,
                anomaly_type=AnomalyType.LOCATION_BASED,
                risk_level=risk_level,
                confidence=confidence,
                description=f"Unusual location: {event.location}",
                detected_at=datetime.now(),
                triggering_events=[event.event_id],
                baseline_behavior={
                    'typical_locations': dict(profile.typical_locations)
                },
                anomalous_behavior={
                    'current_location': event.location,
                    'location_frequency': location_frequency
                },
                recommended_actions=['verify_user_identity', 'require_mfa']
            )
        
        return None
    
    def _detect_device_anomaly(self, event: BehavioralEvent, profile: UserBehavioralProfile) -> Optional[AnomalyDetection]:
        """Detect device-based anomalies"""
        if not event.device_id:
            return None
        
        total_device_events = sum(profile.typical_devices.values())
        if total_device_events < 5:  # Not enough data
            return None
        
        device_frequency = profile.typical_devices.get(event.device_id, 0) / total_device_events
        
        # Check if this is a new or very rare device
        if device_frequency == 0:  # Completely new device
            return AnomalyDetection(
                anomaly_id=f"device_anomaly_{event.event_id}",
                user_id=event.user_id,
                anomaly_type=AnomalyType.DEVICE_BASED,
                risk_level=RiskLevel.HIGH,
                confidence=1.0,
                description=f"New device detected: {event.device_id}",
                detected_at=datetime.now(),
                triggering_events=[event.event_id],
                baseline_behavior={
                    'typical_devices': dict(profile.typical_devices)
                },
                anomalous_behavior={
                    'new_device': event.device_id,
                    'device_frequency': device_frequency
                },
                recommended_actions=['require_device_registration', 'require_mfa', 'limit_session_duration']
            )
        
        return None
    
    def _detect_volume_anomaly(self, event: BehavioralEvent, profile: UserBehavioralProfile) -> Optional[AnomalyDetection]:
        """Detect volume-based anomalies"""
        if event.data_volume == 0:
            return None
        
        # Get recent volume data
        current_hour = event.timestamp.strftime('%Y-%m-%d-%H')
        recent_volumes = []
        
        for time_bucket, volume in profile.data_access_volume.items():
            bucket_time = datetime.strptime(time_bucket, '%Y-%m-%d-%H')
            if (event.timestamp - bucket_time).days <= 7:  # Last 7 days
                recent_volumes.append(volume)
        
        if len(recent_volumes) < 5:  # Not enough data
            return None
        
        # Calculate statistics
        mean_volume = np.mean(recent_volumes)
        std_volume = np.std(recent_volumes)
        
        if std_volume == 0:  # No variation
            return None
        
        # Check if current volume is anomalous (more than 3 standard deviations)
        z_score = abs(event.data_volume - mean_volume) / std_volume
        
        if z_score > 3:
            confidence = min(z_score / 5, 1.0)  # Normalize to 0-1
            risk_level = RiskLevel.HIGH if z_score > 5 else RiskLevel.MEDIUM
            
            return AnomalyDetection(
                anomaly_id=f"volume_anomaly_{event.event_id}",
                user_id=event.user_id,
                anomaly_type=AnomalyType.VOLUME_BASED,
                risk_level=risk_level,
                confidence=confidence,
                description=f"Unusual data access volume: {event.data_volume} (typical: {mean_volume:.1f}±{std_volume:.1f})",
                detected_at=datetime.now(),
                triggering_events=[event.event_id],
                baseline_behavior={
                    'mean_volume': mean_volume,
                    'std_volume': std_volume,
                    'recent_volumes': recent_volumes
                },
                anomalous_behavior={
                    'current_volume': event.data_volume,
                    'z_score': z_score
                },
                recommended_actions=['monitor_data_access', 'check_for_data_exfiltration']
            )
        
        return None
    
    def analyze_user_behavior(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Comprehensive behavioral analysis for a user"""
        if user_id not in self.user_profiles:
            return {'error': 'User profile not found'}
        
        profile = self.user_profiles[user_id]
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get user events from the specified period
        user_events = [
            event for event in self.events
            if event.user_id == user_id and event.timestamp >= cutoff_date
        ]
        
        if not user_events:
            return {'error': 'No events found for the specified period'}
        
        # Analyze patterns
        analysis = {
            'user_id': user_id,
            'analysis_period_days': days,
            'total_events': len(user_events),
            'profile_created': profile.created_at.isoformat(),
            'last_updated': profile.last_updated.isoformat(),
            'patterns': {},
            'anomalies': [],
            'risk_assessment': {},
            'recommendations': []
        }
        
        # Time patterns
        analysis['patterns']['time'] = {
            'most_active_hours': sorted(profile.typical_login_hours.items(), 
                                      key=lambda x: x[1], reverse=True)[:5],
            'most_active_days': sorted(profile.typical_login_days.items(), 
                                     key=lambda x: x[1], reverse=True)[:7],
            'session_patterns': self._analyze_session_patterns(user_events)
        }
        
        # Location patterns
        analysis['patterns']['location'] = {
            'primary_locations': sorted(profile.typical_locations.items(), 
                                      key=lambda x: x[1], reverse=True)[:10],
            'location_diversity': len(profile.typical_locations),
            'location_consistency': self._calculate_location_consistency(profile)
        }
        
        # Device patterns
        analysis['patterns']['device'] = {
            'primary_devices': sorted(profile.typical_devices.items(), 
                                    key=lambda x: x[1], reverse=True)[:5],
            'device_diversity': len(profile.typical_devices),
            'device_switching_frequency': self._calculate_device_switching_frequency(user_events)
        }
        
        # Activity patterns
        analysis['patterns']['activity'] = {
            'most_accessed_resources': sorted(profile.typical_resources.items(), 
                                            key=lambda x: x[1], reverse=True)[:10],
            'most_common_actions': sorted(profile.typical_actions.items(), 
                                        key=lambda x: x[1], reverse=True)[:10],
            'activity_diversity': len(profile.typical_resources) + len(profile.typical_actions)
        }
        
        # Get recent anomalies for this user
        user_anomalies = [
            anomaly for anomaly in self.anomaly_detections
            if anomaly.user_id == user_id and anomaly.detected_at >= cutoff_date
        ]
        
        analysis['anomalies'] = [
            {
                'type': anomaly.anomaly_type.value,
                'risk_level': anomaly.risk_level.value,
                'confidence': anomaly.confidence,
                'description': anomaly.description,
                'detected_at': anomaly.detected_at.isoformat()
            }
            for anomaly in user_anomalies
        ]
        
        # Risk assessment
        analysis['risk_assessment'] = self._assess_user_risk(profile, user_anomalies)
        
        # Generate recommendations
        analysis['recommendations'] = self._generate_recommendations(profile, user_anomalies)
        
        return analysis
    
    def _analyze_session_patterns(self, events: List[BehavioralEvent]) -> Dict[str, Any]:
        """Analyze session patterns from events"""
        sessions = defaultdict(list)
        
        # Group events by session
        for event in events:
            if event.session_id:
                sessions[event.session_id].append(event)
        
        if not sessions:
            return {'error': 'No session data available'}
        
        session_durations = []
        session_event_counts = []
        
        for session_events in sessions.values():
            if len(session_events) > 1:
                start_time = min(event.timestamp for event in session_events)
                end_time = max(event.timestamp for event in session_events)
                duration = (end_time - start_time).total_seconds()
                session_durations.append(duration)
                session_event_counts.append(len(session_events))
        
        if not session_durations:
            return {'error': 'Insufficient session data'}
        
        return {
            'average_duration_seconds': np.mean(session_durations),
            'median_duration_seconds': np.median(session_durations),
            'average_events_per_session': np.mean(session_event_counts),
            'total_sessions': len(sessions),
            'session_duration_std': np.std(session_durations)
        }
    
    def _calculate_location_consistency(self, profile: UserBehavioralProfile) -> float:
        """Calculate location consistency score"""
        if not profile.typical_locations:
            return 0.0
        
        total_events = sum(profile.typical_locations.values())
        if total_events == 0:
            return 0.0
        
        # Calculate entropy (lower entropy = more consistent)
        entropy = 0.0
        for count in profile.typical_locations.values():
            if count > 0:
                p = count / total_events
                entropy -= p * np.log2(p)
        
        # Normalize entropy to 0-1 scale (1 = most consistent)
        max_entropy = np.log2(len(profile.typical_locations))
        if max_entropy == 0:
            return 1.0
        
        consistency = 1.0 - (entropy / max_entropy)
        return consistency
    
    def _calculate_device_switching_frequency(self, events: List[BehavioralEvent]) -> float:
        """Calculate how frequently user switches devices"""
        if len(events) < 2:
            return 0.0
        
        device_switches = 0
        prev_device = None
        
        for event in sorted(events, key=lambda x: x.timestamp):
            if event.device_id and prev_device and event.device_id != prev_device:
                device_switches += 1
            prev_device = event.device_id
        
        return device_switches / len(events)
    
    def _assess_user_risk(self, profile: UserBehavioralProfile, anomalies: List[AnomalyDetection]) -> Dict[str, Any]:
        """Assess overall user risk based on profile and anomalies"""
        risk_score = 0.0
        risk_factors = []
        
        # Anomaly-based risk
        high_risk_anomalies = [a for a in anomalies if a.risk_level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]]
        if high_risk_anomalies:
            risk_score += 0.4
            risk_factors.append(f"{len(high_risk_anomalies)} high-risk anomalies detected")
        
        medium_risk_anomalies = [a for a in anomalies if a.risk_level == RiskLevel.MEDIUM]
        if len(medium_risk_anomalies) > 5:
            risk_score += 0.2
            risk_factors.append(f"{len(medium_risk_anomalies)} medium-risk anomalies detected")
        
        # Behavioral consistency risk
        location_consistency = self._calculate_location_consistency(profile)
        if location_consistency < 0.3:  # Very inconsistent locations
            risk_score += 0.2
            risk_factors.append("Highly inconsistent location patterns")
        
        # Device diversity risk
        if len(profile.typical_devices) > 10:  # Too many devices
            risk_score += 0.1
            risk_factors.append("High device diversity")
        
        # Time pattern risk
        total_hour_events = sum(profile.typical_login_hours.values())
        if total_hour_events > 0:
            night_activity = sum(profile.typical_login_hours.get(h, 0) for h in range(0, 6))
            night_ratio = night_activity / total_hour_events
            if night_ratio > 0.3:  # More than 30% activity at night
                risk_score += 0.1
                risk_factors.append("High nighttime activity")
        
        # Determine risk level
        if risk_score >= 0.8:
            risk_level = RiskLevel.VERY_HIGH
        elif risk_score >= 0.6:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 0.4:
            risk_level = RiskLevel.MEDIUM
        elif risk_score >= 0.2:
            risk_level = RiskLevel.LOW
        else:
            risk_level = RiskLevel.VERY_LOW
        
        return {
            'risk_score': min(risk_score, 1.0),
            'risk_level': risk_level.value,
            'risk_factors': risk_factors,
            'total_anomalies': len(anomalies),
            'high_risk_anomalies': len(high_risk_anomalies)
        }
    
    def _generate_recommendations(self, profile: UserBehavioralProfile, anomalies: List[AnomalyDetection]) -> List[str]:
        """Generate security recommendations based on behavioral analysis"""
        recommendations = []
        
        # Anomaly-based recommendations
        high_risk_anomalies = [a for a in anomalies if a.risk_level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]]
        if high_risk_anomalies:
            recommendations.append("Implement additional authentication requirements")
            recommendations.append("Increase session monitoring frequency")
        
        # Device-based recommendations
        if len(profile.typical_devices) > 5:
            recommendations.append("Consider implementing device registration requirements")
        
        # Location-based recommendations
        location_consistency = self._calculate_location_consistency(profile)
        if location_consistency < 0.5:
            recommendations.append("Enable location-based access controls")
            recommendations.append("Require additional verification for new locations")
        
        # Time-based recommendations
        total_hour_events = sum(profile.typical_login_hours.values())
        if total_hour_events > 0:
            night_activity = sum(profile.typical_login_hours.get(h, 0) for h in range(0, 6))
            night_ratio = night_activity / total_hour_events
            if night_ratio > 0.2:
                recommendations.append("Implement time-based access restrictions")
        
        # General recommendations
        if not recommendations:
            recommendations.append("Current behavioral patterns appear normal")
            recommendations.append("Continue regular monitoring")
        
        return recommendations
    
    def train_ml_models(self):
        """Train ML models on collected behavioral data"""
        if len(self.user_profiles) < 10:  # Need minimum data
            logger.warning("Insufficient data to train ML models")
            return
        
        # Prepare feature matrix
        features = []
        user_ids = []
        
        for user_id, profile in self.user_profiles.items():
            feature_vector = self._extract_features(profile)
            if feature_vector is not None:
                features.append(feature_vector)
                user_ids.append(user_id)
        
        if len(features) < 5:
            logger.warning("Insufficient feature vectors for training")
            return
        
        features_array = np.array(features)
        
        # Scale features
        features_scaled = self.scaler.fit_transform(features_array)
        
        # Apply PCA for dimensionality reduction
        if features_scaled.shape[1] > 10:
            features_pca = self.pca.fit_transform(features_scaled)
        else:
            features_pca = features_scaled
        
        # Train anomaly detection model
        self.anomaly_detector.fit(features_pca)
        
        # Train clustering model
        cluster_labels = self.clustering_model.fit_predict(features_pca)
        
        # Update user profiles with cluster information
        for i, user_id in enumerate(user_ids):
            self.user_profiles[user_id].cluster_id = cluster_labels[i]
            self.user_profiles[user_id].feature_vector = features_pca[i]
        
        # Save models
        self._save_models()
        
        logger.info(f"ML models trained on {len(features)} user profiles")
    
    def _extract_features(self, profile: UserBehavioralProfile) -> Optional[np.ndarray]:
        """Extract feature vector from user profile"""
        try:
            features = []
            
            # Time-based features
            total_hour_events = sum(profile.typical_login_hours.values())
            if total_hour_events > 0:
                # Hour distribution (24 features)
                hour_dist = [profile.typical_login_hours.get(h, 0) / total_hour_events for h in range(24)]
                features.extend(hour_dist)
                
                # Day distribution (7 features)
                total_day_events = sum(profile.typical_login_days.values())
                day_dist = [profile.typical_login_days.get(d, 0) / total_day_events for d in range(7)]
                features.extend(day_dist)
            else:
                features.extend([0] * 31)  # 24 + 7 zeros
            
            # Location features
            features.append(len(profile.typical_locations))  # Location diversity
            features.append(self._calculate_location_consistency(profile))  # Location consistency
            
            # Device features
            features.append(len(profile.typical_devices))  # Device diversity
            
            # Activity features
            features.append(len(profile.typical_resources))  # Resource diversity
            features.append(len(profile.typical_actions))   # Action diversity
            
            # Volume features
            if profile.data_access_volume:
                volumes = list(profile.data_access_volume.values())
                features.append(np.mean(volumes))  # Average volume
                features.append(np.std(volumes))   # Volume variability
            else:
                features.extend([0, 0])
            
            return np.array(features)
            
        except Exception as e:
            logger.error(f"Feature extraction failed for user {profile.user_id}: {e}")
            return None
    
    def _save_models(self):
        """Save trained ML models"""
        try:
            joblib.dump(self.anomaly_detector, os.path.join(self.model_path, 'anomaly_detector.joblib'))
            joblib.dump(self.clustering_model, os.path.join(self.model_path, 'clustering_model.joblib'))
            joblib.dump(self.scaler, os.path.join(self.model_path, 'scaler.joblib'))
            joblib.dump(self.pca, os.path.join(self.model_path, 'pca.joblib'))
            logger.info("ML models saved successfully")
        except Exception as e:
            logger.error(f"Failed to save models: {e}")
    
    def get_analytics_dashboard(self) -> Dict[str, Any]:
        """Get behavioral analytics dashboard data"""
        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        
        # Recent events
        recent_events = [e for e in self.events if e.timestamp >= last_24h]
        weekly_events = [e for e in self.events if e.timestamp >= last_7d]
        
        # Recent anomalies
        recent_anomalies = [a for a in self.anomaly_detections if a.detected_at >= last_24h]
        weekly_anomalies = [a for a in self.anomaly_detections if a.detected_at >= last_7d]
        
        # Risk distribution
        risk_distribution = defaultdict(int)
        for profile in self.user_profiles.values():
            risk_assessment = self._assess_user_risk(profile, [])
            risk_distribution[risk_assessment['risk_level']] += 1
        
        return {
            'timestamp': now.isoformat(),
            'events': {
                'total_events': len(self.events),
                'events_24h': len(recent_events),
                'events_7d': len(weekly_events),
                'unique_users_24h': len(set(e.user_id for e in recent_events)),
                'unique_users_7d': len(set(e.user_id for e in weekly_events))
            },
            'profiles': {
                'total_profiles': len(self.user_profiles),
                'profiles_with_sufficient_data': len([p for p in self.user_profiles.values() 
                                                    if sum(p.typical_login_hours.values()) >= 50])
            },
            'anomalies': {
                'total_anomalies': len(self.anomaly_detections),
                'anomalies_24h': len(recent_anomalies),
                'anomalies_7d': len(weekly_anomalies),
                'high_risk_anomalies_24h': len([a for a in recent_anomalies 
                                              if a.risk_level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]]),
                'anomaly_types_24h': dict(defaultdict(int, 
                    [(a.anomaly_type.value, 1) for a in recent_anomalies]))
            },
            'risk_distribution': dict(risk_distribution),
            'ml_models': {
                'anomaly_detector_trained': hasattr(self.anomaly_detector, 'predict'),
                'clustering_model_trained': hasattr(self.clustering_model, 'labels_'),
                'total_clusters': len(set(p.cluster_id for p in self.user_profiles.values() 
                                        if p.cluster_id is not None)) if any(p.cluster_id is not None 
                                        for p in self.user_profiles.values()) else 0
            }
        }

# Example usage and testing
if __name__ == "__main__":
    # Initialize behavioral analytics engine
    analytics = BehavioralAnalyticsEngine()
    
    # Create sample events
    sample_events = [
        BehavioralEvent(
            event_id="event_1",
            user_id="user_123",
            event_type="login",
            timestamp=datetime.now() - timedelta(hours=1),
            location="New York",
            device_id="device_abc",
            ip_address="192.168.1.100",
            resource_accessed="dashboard",
            action_performed="view",
            data_volume=1024
        ),
        BehavioralEvent(
            event_id="event_2",
            user_id="user_123",
            event_type="data_access",
            timestamp=datetime.now() - timedelta(minutes=30),
            location="New York",
            device_id="device_abc",
            ip_address="192.168.1.100",
            resource_accessed="trading_data",
            action_performed="download",
            data_volume=50000  # Unusually high volume
        )
    ]
    
    # Record events
    for event in sample_events:
        analytics.record_event(event)
    
    # Analyze user behavior
    analysis = analytics.analyze_user_behavior("user_123", days=7)
    print(f"Behavioral analysis: {json.dumps(analysis, indent=2, default=str)}")
    
    # Get dashboard data
    dashboard = analytics.get_analytics_dashboard()
    print(f"Analytics dashboard: {json.dumps(dashboard, indent=2, default=str)}")