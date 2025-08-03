#!/usr/bin/env python3
"""
Behavioral Analytics for Anomaly Detection
Provides comprehensive behavioral analysis and anomaly detection capabilities
"""

import asyncio
import json
import logging
import numpy as np
import statistics
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BehaviorType(Enum):
    """Types of behavioral patterns"""
    LOGIN_PATTERN = "LOGIN_PATTERN"
    TRADING_PATTERN = "TRADING_PATTERN"
    NAVIGATION_PATTERN = "NAVIGATION_PATTERN"
    API_USAGE_PATTERN = "API_USAGE_PATTERN"
    TRANSACTION_PATTERN = "TRANSACTION_PATTERN"

class AnomalyType(Enum):
    """Types of anomalies"""
    STATISTICAL = "STATISTICAL"
    TEMPORAL = "TEMPORAL"
    BEHAVIORAL = "BEHAVIORAL"
    CONTEXTUAL = "CONTEXTUAL"

class RiskLevel(Enum):
    """Risk levels for anomalies"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class BehaviorEvent:
    """Individual behavior event"""
    event_id: str
    user_id: str
    event_type: str
    timestamp: datetime
    attributes: Dict[str, Any]
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BehaviorProfile:
    """User behavior profile"""
    user_id: str
    behavior_type: BehaviorType
    baseline_metrics: Dict[str, float]
    recent_metrics: Dict[str, float]
    anomaly_threshold: float
    last_updated: datetime
    sample_count: int = 0

@dataclass
class AnomalyDetection:
    """Anomaly detection result"""
    detection_id: str
    user_id: str
    anomaly_type: AnomalyType
    behavior_type: BehaviorType
    risk_level: RiskLevel
    confidence_score: float
    description: str
    detected_at: datetime
    attributes: Dict[str, Any]
    resolved: bool = False

class BehavioralAnalyzer:
    """Behavioral analytics and anomaly detection system"""
    
    def __init__(self, learning_period_days: int = 30):
        self.learning_period_days = learning_period_days
        self.behavior_events: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.behavior_profiles: Dict[Tuple[str, BehaviorType], BehaviorProfile] = {}
        self.anomaly_detections: List[AnomalyDetection] = []
        self.ml_models: Dict[str, Any] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        
        # Initialize ML models
        self._initialize_ml_models()
        
        logger.info("Behavioral Analyzer initialized")
    
    def _initialize_ml_models(self):
        """Initialize machine learning models for anomaly detection"""
        # Isolation Forest for general anomaly detection
        self.ml_models['isolation_forest'] = IsolationForest(
            contamination=0.1,  # Expect 10% anomalies
            random_state=42,
            n_estimators=100
        )
        
        # Scalers for feature normalization
        for behavior_type in BehaviorType:
            self.scalers[behavior_type.value] = StandardScaler()
    
    async def record_behavior_event(self, event: BehaviorEvent):
        """Record a behavior event"""
        self.behavior_events[event.user_id].append(event)
        
        # Update behavior profile
        await self._update_behavior_profile(event)
        
        # Check for anomalies
        await self._detect_anomalies(event)
        
        logger.debug(f"Recorded behavior event: {event.event_type} for user {event.user_id}")
    
    async def _update_behavior_profile(self, event: BehaviorEvent):
        """Update user behavior profile"""
        behavior_type = self._classify_behavior_type(event)
        profile_key = (event.user_id, behavior_type)
        
        if profile_key not in self.behavior_profiles:
            # Create new profile
            self.behavior_profiles[profile_key] = BehaviorProfile(
                user_id=event.user_id,
                behavior_type=behavior_type,
                baseline_metrics={},
                recent_metrics={},
                anomaly_threshold=2.0,  # 2 standard deviations
                last_updated=datetime.now()
            )
        
        profile = self.behavior_profiles[profile_key]
        
        # Extract metrics from event
        metrics = self._extract_behavior_metrics(event, behavior_type)
        
        # Update recent metrics
        for metric_name, value in metrics.items():
            if metric_name not in profile.recent_metrics:
                profile.recent_metrics[metric_name] = []
            
            # Keep rolling window of recent values
            if not isinstance(profile.recent_metrics[metric_name], list):
                profile.recent_metrics[metric_name] = [profile.recent_metrics[metric_name]]
            
            profile.recent_metrics[metric_name].append(value)
            
            # Keep only recent values (last 100 events)
            if len(profile.recent_metrics[metric_name]) > 100:
                profile.recent_metrics[metric_name] = profile.recent_metrics[metric_name][-100:]
        
        # Update baseline if enough samples
        profile.sample_count += 1
        if profile.sample_count >= 50:  # Need minimum samples for baseline
            await self._update_baseline_metrics(profile)
        
        profile.last_updated = datetime.now()
    
    def _classify_behavior_type(self, event: BehaviorEvent) -> BehaviorType:
        """Classify the type of behavior based on event"""
        event_type = event.event_type.lower()
        
        if 'login' in event_type or 'auth' in event_type:
            return BehaviorType.LOGIN_PATTERN
        elif 'trade' in event_type or 'order' in event_type:
            return BehaviorType.TRADING_PATTERN
        elif 'api' in event_type or 'request' in event_type:
            return BehaviorType.API_USAGE_PATTERN
        elif 'transaction' in event_type or 'payment' in event_type:
            return BehaviorType.TRANSACTION_PATTERN
        else:
            return BehaviorType.NAVIGATION_PATTERN
    
    def _extract_behavior_metrics(self, event: BehaviorEvent, behavior_type: BehaviorType) -> Dict[str, float]:
        """Extract relevant metrics from behavior event"""
        metrics = {}
        
        # Common metrics
        metrics['hour_of_day'] = event.timestamp.hour
        metrics['day_of_week'] = event.timestamp.weekday()
        
        if behavior_type == BehaviorType.LOGIN_PATTERN:
            metrics['session_duration'] = event.attributes.get('session_duration', 0)
            metrics['failed_attempts'] = event.attributes.get('failed_attempts', 0)
            metrics['new_device'] = 1.0 if event.attributes.get('new_device', False) else 0.0
            metrics['unusual_location'] = 1.0 if event.attributes.get('unusual_location', False) else 0.0
            
        elif behavior_type == BehaviorType.TRADING_PATTERN:
            metrics['order_size'] = float(event.attributes.get('order_size', 0))
            metrics['order_frequency'] = event.attributes.get('order_frequency', 0)
            metrics['risk_amount'] = float(event.attributes.get('risk_amount', 0))
            metrics['symbols_traded'] = event.attributes.get('symbols_traded', 1)
            
        elif behavior_type == BehaviorType.API_USAGE_PATTERN:
            metrics['requests_per_minute'] = event.attributes.get('requests_per_minute', 0)
            metrics['response_time'] = event.attributes.get('response_time', 0)
            metrics['error_rate'] = event.attributes.get('error_rate', 0)
            
        elif behavior_type == BehaviorType.TRANSACTION_PATTERN:
            metrics['transaction_amount'] = float(event.attributes.get('amount', 0))
            metrics['transaction_frequency'] = event.attributes.get('frequency', 0)
            metrics['unusual_counterparty'] = 1.0 if event.attributes.get('unusual_counterparty', False) else 0.0
        
        return metrics
    
    async def _update_baseline_metrics(self, profile: BehaviorProfile):
        """Update baseline metrics using statistical analysis"""
        for metric_name, recent_values in profile.recent_metrics.items():
            if isinstance(recent_values, list) and len(recent_values) >= 10:
                # Calculate statistical baseline
                profile.baseline_metrics[metric_name] = {
                    'mean': statistics.mean(recent_values),
                    'std': statistics.stdev(recent_values) if len(recent_values) > 1 else 0,
                    'median': statistics.median(recent_values),
                    'min': min(recent_values),
                    'max': max(recent_values)
                }
    
    async def _detect_anomalies(self, event: BehaviorEvent):
        """Detect anomalies in behavior"""
        behavior_type = self._classify_behavior_type(event)
        profile_key = (event.user_id, behavior_type)
        
        if profile_key not in self.behavior_profiles:
            return  # No profile yet
        
        profile = self.behavior_profiles[profile_key]
        
        if not profile.baseline_metrics:
            return  # No baseline yet
        
        # Extract current metrics
        current_metrics = self._extract_behavior_metrics(event, behavior_type)
        
        # Statistical anomaly detection
        anomalies = await self._detect_statistical_anomalies(profile, current_metrics)
        
        # Temporal anomaly detection
        temporal_anomalies = await self._detect_temporal_anomalies(event, profile)
        
        # ML-based anomaly detection
        ml_anomalies = await self._detect_ml_anomalies(event, profile, current_metrics)
        
        # Combine all anomalies
        all_anomalies = anomalies + temporal_anomalies + ml_anomalies
        
        # Create anomaly detections
        for anomaly_info in all_anomalies:
            detection = AnomalyDetection(
                detection_id=f"ANOM_{int(datetime.now().timestamp() * 1000)}",
                user_id=event.user_id,
                anomaly_type=anomaly_info['type'],
                behavior_type=behavior_type,
                risk_level=anomaly_info['risk_level'],
                confidence_score=anomaly_info['confidence'],
                description=anomaly_info['description'],
                detected_at=datetime.now(),
                attributes=anomaly_info.get('attributes', {})
            )
            
            self.anomaly_detections.append(detection)
            
            # Log high-risk anomalies
            if detection.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                logger.warning(f"High-risk anomaly detected: {detection.description}")
    
    async def _detect_statistical_anomalies(self, profile: BehaviorProfile, 
                                          current_metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        """Detect statistical anomalies using z-score analysis"""
        anomalies = []
        
        for metric_name, current_value in current_metrics.items():
            if metric_name in profile.baseline_metrics:
                baseline = profile.baseline_metrics[metric_name]
                mean = baseline['mean']
                std = baseline['std']
                
                if std > 0:  # Avoid division by zero
                    z_score = abs((current_value - mean) / std)
                    
                    if z_score > profile.anomaly_threshold:
                        # Determine risk level based on z-score
                        if z_score > 4:
                            risk_level = RiskLevel.CRITICAL
                        elif z_score > 3:
                            risk_level = RiskLevel.HIGH
                        elif z_score > 2.5:
                            risk_level = RiskLevel.MEDIUM
                        else:
                            risk_level = RiskLevel.LOW
                        
                        anomalies.append({
                            'type': AnomalyType.STATISTICAL,
                            'risk_level': risk_level,
                            'confidence': min(0.99, z_score / 5.0),  # Normalize to 0-1
                            'description': f"Statistical anomaly in {metric_name}: {current_value:.2f} (z-score: {z_score:.2f})",
                            'attributes': {
                                'metric': metric_name,
                                'current_value': current_value,
                                'baseline_mean': mean,
                                'z_score': z_score
                            }
                        })
        
        return anomalies
    
    async def _detect_temporal_anomalies(self, event: BehaviorEvent, 
                                       profile: BehaviorProfile) -> List[Dict[str, Any]]:
        """Detect temporal anomalies (unusual timing patterns)"""
        anomalies = []
        
        # Check for unusual time patterns
        hour = event.timestamp.hour
        day_of_week = event.timestamp.weekday()
        
        # Business hours check (assuming 9 AM - 5 PM, Mon-Fri)
        if hour < 9 or hour > 17 or day_of_week >= 5:
            # Check if user typically operates during business hours
            user_events = list(self.behavior_events[event.user_id])
            if len(user_events) > 10:
                business_hour_events = [
                    e for e in user_events[-50:]  # Last 50 events
                    if 9 <= e.timestamp.hour <= 17 and e.timestamp.weekday() < 5
                ]
                
                if len(business_hour_events) / len(user_events[-50:]) > 0.8:  # Usually works business hours
                    anomalies.append({
                        'type': AnomalyType.TEMPORAL,
                        'risk_level': RiskLevel.MEDIUM,
                        'confidence': 0.7,
                        'description': f"Unusual activity time: {event.timestamp.strftime('%H:%M on %A')}",
                        'attributes': {
                            'hour': hour,
                            'day_of_week': day_of_week,
                            'typical_business_hours': True
                        }
                    })
        
        return anomalies
    
    async def _detect_ml_anomalies(self, event: BehaviorEvent, profile: BehaviorProfile,
                                 current_metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        """Detect anomalies using machine learning models"""
        anomalies = []
        
        try:
            # Prepare feature vector
            feature_names = sorted(current_metrics.keys())
            features = np.array([[current_metrics[name] for name in feature_names]])
            
            # Use Isolation Forest for anomaly detection
            model = self.ml_models['isolation_forest']
            
            # Check if model is trained (has enough data)
            user_events = list(self.behavior_events[event.user_id])
            if len(user_events) >= 50:  # Need minimum samples for ML
                # Prepare training data from recent events
                training_features = []
                for past_event in user_events[-100:]:  # Last 100 events
                    past_behavior_type = self._classify_behavior_type(past_event)
                    if past_behavior_type == profile.behavior_type:
                        past_metrics = self._extract_behavior_metrics(past_event, past_behavior_type)
                        feature_vector = [past_metrics.get(name, 0) for name in feature_names]
                        training_features.append(feature_vector)
                
                if len(training_features) >= 10:
                    training_data = np.array(training_features)
                    
                    # Fit scaler and model
                    scaler = self.scalers[profile.behavior_type.value]
                    scaled_training = scaler.fit_transform(training_data)
                    model.fit(scaled_training)
                    
                    # Predict anomaly for current event
                    scaled_features = scaler.transform(features)
                    anomaly_score = model.decision_function(scaled_features)[0]
                    is_anomaly = model.predict(scaled_features)[0] == -1
                    
                    if is_anomaly:
                        # Convert anomaly score to confidence (more negative = more anomalous)
                        confidence = min(0.95, abs(anomaly_score) / 2.0)
                        
                        # Determine risk level based on anomaly score
                        if anomaly_score < -0.5:
                            risk_level = RiskLevel.HIGH
                        elif anomaly_score < -0.3:
                            risk_level = RiskLevel.MEDIUM
                        else:
                            risk_level = RiskLevel.LOW
                        
                        anomalies.append({
                            'type': AnomalyType.BEHAVIORAL,
                            'risk_level': risk_level,
                            'confidence': confidence,
                            'description': f"ML-detected behavioral anomaly (score: {anomaly_score:.3f})",
                            'attributes': {
                                'anomaly_score': anomaly_score,
                                'model_type': 'isolation_forest',
                                'feature_count': len(feature_names)
                            }
                        })
        
        except Exception as e:
            logger.error(f"ML anomaly detection error: {e}")
        
        return anomalies
    
    def get_user_behavior_profile(self, user_id: str, 
                                 behavior_type: Optional[BehaviorType] = None) -> List[BehaviorProfile]:
        """Get behavior profile(s) for a user"""
        profiles = []
        
        for (uid, btype), profile in self.behavior_profiles.items():
            if uid == user_id and (behavior_type is None or btype == behavior_type):
                profiles.append(profile)
        
        return profiles
    
    def get_anomaly_detections(self, user_id: Optional[str] = None,
                              risk_level: Optional[RiskLevel] = None,
                              hours_back: int = 24,
                              limit: int = 100) -> List[AnomalyDetection]:
        """Get anomaly detections with filtering"""
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        detections = [
            d for d in self.anomaly_detections
            if d.detected_at >= cutoff_time
        ]
        
        if user_id:
            detections = [d for d in detections if d.user_id == user_id]
        
        if risk_level:
            detections = [d for d in detections if d.risk_level == risk_level]
        
        # Sort by detection time (newest first)
        detections.sort(key=lambda x: x.detected_at, reverse=True)
        
        return detections[:limit]
    
    def get_behavior_summary(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive behavior summary for a user"""
        profiles = self.get_user_behavior_profile(user_id)
        recent_anomalies = self.get_anomaly_detections(user_id, hours_back=24)
        
        # Calculate overall risk score
        risk_scores = []
        for anomaly in recent_anomalies:
            if anomaly.risk_level == RiskLevel.CRITICAL:
                risk_scores.append(1.0)
            elif anomaly.risk_level == RiskLevel.HIGH:
                risk_scores.append(0.8)
            elif anomaly.risk_level == RiskLevel.MEDIUM:
                risk_scores.append(0.5)
            else:
                risk_scores.append(0.2)
        
        overall_risk = statistics.mean(risk_scores) if risk_scores else 0.0
        
        return {
            'user_id': user_id,
            'behavior_profiles': len(profiles),
            'recent_anomalies': len(recent_anomalies),
            'overall_risk_score': overall_risk,
            'risk_level': self._risk_score_to_level(overall_risk),
            'last_activity': max([p.last_updated for p in profiles]) if profiles else None,
            'anomaly_breakdown': {
                level.value: len([a for a in recent_anomalies if a.risk_level == level])
                for level in RiskLevel
            }
        }
    
    def _risk_score_to_level(self, score: float) -> RiskLevel:
        """Convert risk score to risk level"""
        if score >= 0.8:
            return RiskLevel.CRITICAL
        elif score >= 0.6:
            return RiskLevel.HIGH
        elif score >= 0.3:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    async def train_models(self, user_id: Optional[str] = None):
        """Train ML models with accumulated data"""
        logger.info("Training behavioral analysis models...")
        
        users_to_train = [user_id] if user_id else list(self.behavior_events.keys())
        
        for uid in users_to_train:
            events = list(self.behavior_events[uid])
            if len(events) < 50:  # Need minimum data
                continue
            
            # Group events by behavior type
            behavior_groups = defaultdict(list)
            for event in events:
                behavior_type = self._classify_behavior_type(event)
                behavior_groups[behavior_type].append(event)
            
            # Train models for each behavior type
            for behavior_type, type_events in behavior_groups.items():
                if len(type_events) >= 20:  # Minimum for training
                    await self._train_behavior_model(uid, behavior_type, type_events)
        
        logger.info("Model training completed")
    
    async def _train_behavior_model(self, user_id: str, behavior_type: BehaviorType, 
                                  events: List[BehaviorEvent]):
        """Train model for specific user and behavior type"""
        try:
            # Extract features from events
            feature_vectors = []
            for event in events:
                metrics = self._extract_behavior_metrics(event, behavior_type)
                feature_names = sorted(metrics.keys())
                feature_vector = [metrics[name] for name in feature_names]
                feature_vectors.append(feature_vector)
            
            if len(feature_vectors) >= 10:
                training_data = np.array(feature_vectors)
                
                # Fit scaler
                scaler = StandardScaler()
                scaled_data = scaler.fit_transform(training_data)
                
                # Train Isolation Forest
                model = IsolationForest(contamination=0.1, random_state=42)
                model.fit(scaled_data)
                
                # Store trained model and scaler
                model_key = f"{user_id}_{behavior_type.value}"
                self.ml_models[model_key] = model
                self.scalers[model_key] = scaler
                
                logger.debug(f"Trained model for {user_id} - {behavior_type.value}")
        
        except Exception as e:
            logger.error(f"Model training error for {user_id} - {behavior_type.value}: {e}")
    
    def export_behavior_data(self, user_id: str) -> Dict[str, Any]:
        """Export behavior data for external analysis"""
        profiles = self.get_user_behavior_profile(user_id)
        anomalies = self.get_anomaly_detections(user_id, hours_back=24*7)  # Last week
        events = list(self.behavior_events[user_id])
        
        return {
            'user_id': user_id,
            'export_timestamp': datetime.now().isoformat(),
            'behavior_profiles': [
                {
                    'behavior_type': p.behavior_type.value,
                    'baseline_metrics': p.baseline_metrics,
                    'sample_count': p.sample_count,
                    'last_updated': p.last_updated.isoformat()
                }
                for p in profiles
            ],
            'recent_anomalies': [
                {
                    'detection_id': a.detection_id,
                    'anomaly_type': a.anomaly_type.value,
                    'risk_level': a.risk_level.value,
                    'confidence_score': a.confidence_score,
                    'description': a.description,
                    'detected_at': a.detected_at.isoformat(),
                    'attributes': a.attributes
                }
                for a in anomalies
            ],
            'event_count': len(events),
            'date_range': {
                'start': min(e.timestamp for e in events).isoformat() if events else None,
                'end': max(e.timestamp for e in events).isoformat() if events else None
            }
        }