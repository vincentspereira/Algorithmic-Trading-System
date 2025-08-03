#!/usr/bin/env python3
"""
Advanced Fraud Detection System
Provides comprehensive fraud detection using machine learning, behavioral analysis,
transaction monitoring, and automated response capabilities.
"""

import asyncio
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import uuid
import hashlib
import pickle
import os
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import networkx as nx
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FraudRiskLevel(Enum):
    """Fraud risk levels"""
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class FraudType(Enum):
    """Types of fraud"""
    ACCOUNT_TAKEOVER = "ACCOUNT_TAKEOVER"
    IDENTITY_THEFT = "IDENTITY_THEFT"
    TRANSACTION_FRAUD = "TRANSACTION_FRAUD"
    INSIDER_THREAT = "INSIDER_THREAT"
    MONEY_LAUNDERING = "MONEY_LAUNDERING"
    MARKET_MANIPULATION = "MARKET_MANIPULATION"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    DATA_EXFILTRATION = "DATA_EXFILTRATION"

class ResponseAction(Enum):
    """Automated response actions"""
    MONITOR = "MONITOR"
    ALERT = "ALERT"
    CHALLENGE = "CHALLENGE"
    BLOCK = "BLOCK"
    SUSPEND = "SUSPEND"
    ESCALATE = "ESCALATE"
    INVESTIGATE = "INVESTIGATE"

class TransactionType(Enum):
    """Transaction types for monitoring"""
    TRADE = "TRADE"
    TRANSFER = "TRANSFER"
    WITHDRAWAL = "WITHDRAWAL"
    DEPOSIT = "DEPOSIT"
    LOGIN = "LOGIN"
    DATA_ACCESS = "DATA_ACCESS"
    CONFIGURATION = "CONFIGURATION"

@dataclass
class FraudFeatures:
    """Feature set for fraud detection"""
    # User behavior features
    login_frequency_24h: float = 0.0
    login_frequency_7d: float = 0.0
    unusual_login_time: bool = False
    new_device: bool = False
    new_location: bool = False
    location_distance_km: float = 0.0
    session_duration_minutes: float = 0.0
    
    # Transaction features
    transaction_amount: float = 0.0
    transaction_frequency_1h: int = 0
    transaction_frequency_24h: int = 0
    unusual_transaction_time: bool = False
    transaction_velocity: float = 0.0
    amount_deviation_from_avg: float = 0.0
    
    # Network features
    ip_reputation_score: float = 0.5
    vpn_detected: bool = False
    tor_detected: bool = False
    proxy_detected: bool = False
    geolocation_mismatch: bool = False
    
    # Account features
    account_age_days: int = 0
    failed_login_attempts_24h: int = 0
    password_changed_recently: bool = False
    mfa_enabled: bool = False
    
    # Relationship features
    connected_suspicious_accounts: int = 0
    shared_devices: int = 0
    shared_ip_addresses: int = 0
    
    def to_array(self) -> np.ndarray:
        """Convert features to numpy array for ML models"""
        return np.array([
            self.login_frequency_24h,
            self.login_frequency_7d,
            float(self.unusual_login_time),
            float(self.new_device),
            float(self.new_location),
            self.location_distance_km,
            self.session_duration_minutes,
            self.transaction_amount,
            self.transaction_frequency_1h,
            self.transaction_frequency_24h,
            float(self.unusual_transaction_time),
            self.transaction_velocity,
            self.amount_deviation_from_avg,
            self.ip_reputation_score,
            float(self.vpn_detected),
            float(self.tor_detected),
            float(self.proxy_detected),
            float(self.geolocation_mismatch),
            self.account_age_days,
            self.failed_login_attempts_24h,
            float(self.password_changed_recently),
            float(self.mfa_enabled),
            self.connected_suspicious_accounts,
            self.shared_devices,
            self.shared_ip_addresses
        ])

@dataclass
class FraudEvent:
    """Fraud detection event"""
    event_id: str
    user_id: str
    event_type: str
    timestamp: datetime
    features: FraudFeatures
    fraud_score: float = 0.0
    risk_level: FraudRiskLevel = FraudRiskLevel.LOW
    fraud_types: List[FraudType] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class FraudAlert:
    """Fraud alert"""
    alert_id: str
    event_id: str
    user_id: str
    fraud_type: FraudType
    risk_level: FraudRiskLevel
    fraud_score: float
    confidence: float
    description: str
    evidence: Dict[str, Any]
    recommended_actions: List[ResponseAction]
    created_at: datetime
    resolved: bool = False
    resolution_notes: Optional[str] = None

@dataclass
class TransactionGraph:
    """Transaction graph for network analysis"""
    graph: nx.Graph = field(default_factory=nx.Graph)
    user_nodes: Set[str] = field(default_factory=set)
    transaction_edges: Set[Tuple[str, str]] = field(default_factory=set)
    
    def add_transaction(self, from_user: str, to_user: str, amount: float, timestamp: datetime):
        """Add transaction to graph"""
        self.graph.add_edge(from_user, to_user, 
                           weight=amount, 
                           timestamp=timestamp,
                           transaction_id=str(uuid.uuid4()))
        self.user_nodes.add(from_user)
        self.user_nodes.add(to_user)
        self.transaction_edges.add((from_user, to_user))
    
    def detect_suspicious_patterns(self) -> List[Dict[str, Any]]:
        """Detect suspicious patterns in transaction graph"""
        suspicious_patterns = []
        
        # Detect circular transactions (potential money laundering)
        cycles = list(nx.simple_cycles(self.graph))
        for cycle in cycles:
            if len(cycle) >= 3:  # Minimum cycle length
                total_amount = sum(
                    self.graph[cycle[i]][cycle[(i+1) % len(cycle)]].get('weight', 0)
                    for i in range(len(cycle))
                )
                suspicious_patterns.append({
                    'type': 'circular_transaction',
                    'participants': cycle,
                    'total_amount': total_amount,
                    'risk_score': min(total_amount / 10000, 1.0)  # Normalize to 0-1
                })
        
        # Detect hub nodes (potential money mules)
        degree_centrality = nx.degree_centrality(self.graph)
        for node, centrality in degree_centrality.items():
            if centrality > 0.1:  # High centrality threshold
                suspicious_patterns.append({
                    'type': 'hub_node',
                    'user_id': node,
                    'centrality': centrality,
                    'risk_score': centrality
                })
        
        # Detect rapid transaction chains
        for node in self.user_nodes:
            neighbors = list(self.graph.neighbors(node))
            if len(neighbors) > 5:  # High transaction volume
                recent_transactions = []
                for neighbor in neighbors:
                    edge_data = self.graph[node][neighbor]
                    timestamp = edge_data.get('timestamp')
                    if timestamp and (datetime.now() - timestamp).hours < 24:
                        recent_transactions.append(edge_data)
                
                if len(recent_transactions) > 3:
                    suspicious_patterns.append({
                        'type': 'rapid_transaction_chain',
                        'user_id': node,
                        'transaction_count': len(recent_transactions),
                        'risk_score': min(len(recent_transactions) / 10, 1.0)
                    })
        
        return suspicious_patterns

class FraudDetectionEngine:
    """Advanced fraud detection engine with ML and behavioral analysis"""
    
    def __init__(self, model_path: str = "models/fraud"):
        self.model_path = model_path
        self.events: deque = deque(maxlen=50000)
        self.alerts: List[FraudAlert] = []
        self.user_profiles: Dict[str, Dict[str, Any]] = {}
        self.transaction_graph = TransactionGraph()
        
        # ML Models
        self.fraud_classifier = None
        self.anomaly_detector = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        
        # Configuration
        self.config = {
            'fraud_threshold': 0.7,
            'anomaly_threshold': 0.8,
            'model_retrain_interval_hours': 24,
            'alert_retention_days': 90,
            'feature_window_hours': 24,
            'transaction_velocity_threshold': 10,
            'location_distance_threshold_km': 1000
        }
        
        # Response rules
        self.response_rules = {
            FraudRiskLevel.CRITICAL: [ResponseAction.BLOCK, ResponseAction.ESCALATE, ResponseAction.INVESTIGATE],
            FraudRiskLevel.HIGH: [ResponseAction.CHALLENGE, ResponseAction.ALERT, ResponseAction.MONITOR],
            FraudRiskLevel.MEDIUM: [ResponseAction.ALERT, ResponseAction.MONITOR],
            FraudRiskLevel.LOW: [ResponseAction.MONITOR],
            FraudRiskLevel.VERY_LOW: []
        }
        
        # Initialize models
        self._initialize_models()
        
        logger.info("Advanced Fraud Detection Engine initialized")
    
    def _initialize_models(self):
        """Initialize or load ML models"""
        try:
            os.makedirs(self.model_path, exist_ok=True)
            
            # Try to load existing models
            classifier_path = os.path.join(self.model_path, 'fraud_classifier.pkl')
            anomaly_path = os.path.join(self.model_path, 'anomaly_detector.pkl')
            scaler_path = os.path.join(self.model_path, 'scaler.pkl')
            
            if os.path.exists(classifier_path):
                with open(classifier_path, 'rb') as f:
                    self.fraud_classifier = pickle.load(f)
                logger.info("Loaded existing fraud classifier")
            else:
                self.fraud_classifier = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42,
                    class_weight='balanced'
                )
                logger.info("Initialized new fraud classifier")
            
            if os.path.exists(anomaly_path):
                with open(anomaly_path, 'rb') as f:
                    self.anomaly_detector = pickle.load(f)
                logger.info("Loaded existing anomaly detector")
            else:
                self.anomaly_detector = IsolationForest(
                    contamination=0.1,
                    random_state=42,
                    n_estimators=100
                )
                logger.info("Initialized new anomaly detector")
            
            if os.path.exists(scaler_path):
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                logger.info("Loaded existing scaler")
                
        except Exception as e:
            logger.error(f"Error initializing models: {e}")
            # Initialize default models
            self.fraud_classifier = RandomForestClassifier(n_estimators=100, random_state=42)
            self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
    
    def extract_features(self, event_data: Dict[str, Any]) -> FraudFeatures:
        """Extract fraud detection features from event data"""
        user_id = event_data.get('user_id', '')
        timestamp = event_data.get('timestamp', datetime.now())
        
        # Initialize features
        features = FraudFeatures()
        
        # Get user profile
        profile = self.user_profiles.get(user_id, {})
        
        # Calculate time-based features
        features.login_frequency_24h = self._calculate_login_frequency(user_id, hours=24)
        features.login_frequency_7d = self._calculate_login_frequency(user_id, days=7)
        features.unusual_login_time = self._is_unusual_time(timestamp)
        
        # Device and location features
        current_device = event_data.get('device_id', '')
        current_location = event_data.get('location', '')
        
        known_devices = profile.get('devices', set())
        known_locations = profile.get('locations', set())
        
        features.new_device = current_device not in known_devices
        features.new_location = current_location not in known_locations
        
        # Calculate location distance
        if current_location and profile.get('last_location'):
            features.location_distance_km = self._calculate_distance(
                current_location, profile['last_location']
            )
        
        # Session features
        features.session_duration_minutes = event_data.get('session_duration', 0) / 60
        
        # Transaction features
        if event_data.get('transaction_amount'):
            features.transaction_amount = float(event_data['transaction_amount'])
            features.transaction_frequency_1h = self._calculate_transaction_frequency(user_id, hours=1)
            features.transaction_frequency_24h = self._calculate_transaction_frequency(user_id, hours=24)
            features.unusual_transaction_time = self._is_unusual_transaction_time(timestamp)
            features.transaction_velocity = self._calculate_transaction_velocity(user_id)
            features.amount_deviation_from_avg = self._calculate_amount_deviation(user_id, features.transaction_amount)
        
        # Network features
        ip_address = event_data.get('ip_address', '')
        features.ip_reputation_score = self._get_ip_reputation(ip_address)
        features.vpn_detected = event_data.get('vpn_detected', False)
        features.tor_detected = event_data.get('tor_detected', False)
        features.proxy_detected = event_data.get('proxy_detected', False)
        features.geolocation_mismatch = self._check_geolocation_mismatch(ip_address, current_location)
        
        # Account features
        features.account_age_days = (timestamp - profile.get('created_at', timestamp)).days
        features.failed_login_attempts_24h = self._count_failed_logins(user_id, hours=24)
        features.password_changed_recently = self._password_changed_recently(user_id, days=7)
        features.mfa_enabled = profile.get('mfa_enabled', False)
        
        # Relationship features
        features.connected_suspicious_accounts = self._count_connected_suspicious_accounts(user_id)
        features.shared_devices = self._count_shared_devices(user_id, current_device)
        features.shared_ip_addresses = self._count_shared_ips(user_id, ip_address)
        
        return features
    
    def _calculate_login_frequency(self, user_id: str, hours: int = 24, days: int = 0) -> float:
        """Calculate login frequency for user"""
        if days > 0:
            time_window = timedelta(days=days)
        else:
            time_window = timedelta(hours=hours)
        
        cutoff_time = datetime.now() - time_window
        
        login_count = 0
        for event in self.events:
            if (event.user_id == user_id and 
                event.event_type == 'login' and 
                event.timestamp >= cutoff_time):
                login_count += 1
        
        return login_count / max(hours if days == 0 else days * 24, 1)
    
    def _is_unusual_time(self, timestamp: datetime) -> bool:
        """Check if timestamp is at unusual time (outside business hours)"""
        hour = timestamp.hour
        day_of_week = timestamp.weekday()
        
        # Business hours: 6 AM to 10 PM, Monday to Friday
        business_hours = (6, 22)
        business_days = list(range(5))
        
        return (hour < business_hours[0] or 
                hour > business_hours[1] or 
                day_of_week not in business_days)
    
    def _calculate_distance(self, location1: str, location2: str) -> float:
        """Calculate distance between two locations (simplified)"""
        # In a real implementation, this would use geolocation APIs
        # For now, return a mock distance based on string similarity
        if location1 == location2:
            return 0.0
        elif location1.split(',')[0] == location2.split(',')[0]:  # Same city
            return 50.0
        else:
            return 1000.0  # Different cities
    
    def _calculate_transaction_frequency(self, user_id: str, hours: int) -> int:
        """Calculate transaction frequency for user"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        count = 0
        for event in self.events:
            if (event.user_id == user_id and 
                'transaction' in event.event_type.lower() and 
                event.timestamp >= cutoff_time):
                count += 1
        
        return count
    
    def _is_unusual_transaction_time(self, timestamp: datetime) -> bool:
        """Check if transaction time is unusual"""
        # Transactions outside market hours might be suspicious
        hour = timestamp.hour
        day_of_week = timestamp.weekday()
        
        # Market hours: 9 AM to 4 PM, Monday to Friday
        market_hours = (9, 16)
        market_days = list(range(5))
        
        return (hour < market_hours[0] or 
                hour > market_hours[1] or 
                day_of_week not in market_days)
    
    def _calculate_transaction_velocity(self, user_id: str) -> float:
        """Calculate transaction velocity (transactions per hour)"""
        recent_transactions = []
        cutoff_time = datetime.now() - timedelta(hours=1)
        
        for event in self.events:
            if (event.user_id == user_id and 
                'transaction' in event.event_type.lower() and 
                event.timestamp >= cutoff_time):
                recent_transactions.append(event)
        
        return len(recent_transactions)
    
    def _calculate_amount_deviation(self, user_id: str, current_amount: float) -> float:
        """Calculate deviation from user's average transaction amount"""
        user_transactions = []
        
        for event in self.events:
            if (event.user_id == user_id and 
                hasattr(event, 'features') and 
                event.features.transaction_amount > 0):
                user_transactions.append(event.features.transaction_amount)
        
        if len(user_transactions) < 3:
            return 0.0
        
        avg_amount = np.mean(user_transactions)
        std_amount = np.std(user_transactions)
        
        if std_amount == 0:
            return 0.0
        
        return abs(current_amount - avg_amount) / std_amount
    
    def _get_ip_reputation(self, ip_address: str) -> float:
        """Get IP reputation score (0-1, higher is better)"""
        # In a real implementation, this would query threat intelligence feeds
        # For now, return a mock score based on IP characteristics
        if not ip_address:
            return 0.5
        
        # Private IP addresses are generally trusted
        if (ip_address.startswith('192.168.') or 
            ip_address.startswith('10.') or 
            ip_address.startswith('172.')):
            return 0.9
        
        # Mock reputation based on IP hash
        ip_hash = hashlib.md5(ip_address.encode()).hexdigest()
        reputation = int(ip_hash[:2], 16) / 255.0
        
        return reputation
    
    def _check_geolocation_mismatch(self, ip_address: str, declared_location: str) -> bool:
        """Check if IP geolocation matches declared location"""
        # In a real implementation, this would use geolocation services
        # For now, return a mock result
        if not ip_address or not declared_location:
            return False
        
        # Mock geolocation check
        ip_hash = hashlib.md5(ip_address.encode()).hexdigest()
        location_hash = hashlib.md5(declared_location.encode()).hexdigest()
        
        return ip_hash[:2] != location_hash[:2]
    
    def _count_failed_logins(self, user_id: str, hours: int) -> int:
        """Count failed login attempts"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        count = 0
        for event in self.events:
            if (event.user_id == user_id and 
                event.event_type == 'failed_login' and 
                event.timestamp >= cutoff_time):
                count += 1
        
        return count
    
    def _password_changed_recently(self, user_id: str, days: int) -> bool:
        """Check if password was changed recently"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        for event in self.events:
            if (event.user_id == user_id and 
                event.event_type == 'password_change' and 
                event.timestamp >= cutoff_time):
                return True
        
        return False
    
    def _count_connected_suspicious_accounts(self, user_id: str) -> int:
        """Count connected suspicious accounts"""
        # Use transaction graph to find connected accounts
        if user_id not in self.transaction_graph.user_nodes:
            return 0
        
        neighbors = list(self.transaction_graph.graph.neighbors(user_id))
        suspicious_count = 0
        
        for neighbor in neighbors:
            # Check if neighbor has high fraud score
            neighbor_profile = self.user_profiles.get(neighbor, {})
            if neighbor_profile.get('fraud_score', 0) > 0.7:
                suspicious_count += 1
        
        return suspicious_count
    
    def _count_shared_devices(self, user_id: str, device_id: str) -> int:
        """Count how many users share this device"""
        if not device_id:
            return 0
        
        users_with_device = set()
        for uid, profile in self.user_profiles.items():
            if device_id in profile.get('devices', set()):
                users_with_device.add(uid)
        
        return len(users_with_device) - 1  # Exclude current user
    
    def _count_shared_ips(self, user_id: str, ip_address: str) -> int:
        """Count how many users share this IP address"""
        if not ip_address:
            return 0
        
        users_with_ip = set()
        for uid, profile in self.user_profiles.items():
            if ip_address in profile.get('ip_addresses', set()):
                users_with_ip.add(uid)
        
        return len(users_with_ip) - 1  # Exclude current user
    
    def detect_fraud(self, event_data: Dict[str, Any]) -> FraudEvent:
        """Detect fraud for a given event"""
        # Extract features
        features = self.extract_features(event_data)
        
        # Create fraud event
        fraud_event = FraudEvent(
            event_id=str(uuid.uuid4()),
            user_id=event_data.get('user_id', ''),
            event_type=event_data.get('event_type', ''),
            timestamp=event_data.get('timestamp', datetime.now()),
            features=features
        )
        
        # Calculate fraud score using multiple methods
        fraud_scores = []
        
        # Rule-based scoring
        rule_score = self._calculate_rule_based_score(features)
        fraud_scores.append(rule_score)
        
        # ML-based scoring (if model is trained)
        if hasattr(self.fraud_classifier, 'predict_proba'):
            try:
                feature_array = features.to_array().reshape(1, -1)
                feature_array_scaled = self.scaler.transform(feature_array)
                ml_score = self.fraud_classifier.predict_proba(feature_array_scaled)[0][1]
                fraud_scores.append(ml_score)
            except Exception as e:
                logger.warning(f"ML scoring failed: {e}")
        
        # Anomaly detection scoring
        if hasattr(self.anomaly_detector, 'decision_function'):
            try:
                feature_array = features.to_array().reshape(1, -1)
                anomaly_score = self.anomaly_detector.decision_function(feature_array)[0]
                # Convert to 0-1 scale (higher = more anomalous)
                normalized_anomaly = max(0, min(1, (0.5 - anomaly_score) * 2))
                fraud_scores.append(normalized_anomaly)
            except Exception as e:
                logger.warning(f"Anomaly detection failed: {e}")
        
        # Combine scores (weighted average)
        if fraud_scores:
            fraud_event.fraud_score = np.mean(fraud_scores)
            fraud_event.confidence = 1.0 - np.std(fraud_scores) if len(fraud_scores) > 1 else 0.8
        else:
            fraud_event.fraud_score = rule_score
            fraud_event.confidence = 0.6
        
        # Determine risk level
        fraud_event.risk_level = self._determine_risk_level(fraud_event.fraud_score)
        
        # Identify fraud types
        fraud_event.fraud_types = self._identify_fraud_types(features, fraud_event.fraud_score)
        
        # Store event
        self.events.append(fraud_event)
        
        # Update user profile
        self._update_user_profile(fraud_event)
        
        # Generate alerts if necessary
        if fraud_event.risk_level in [FraudRiskLevel.HIGH, FraudRiskLevel.CRITICAL]:
            alert = self._generate_alert(fraud_event)
            self.alerts.append(alert)
            logger.warning(f"Fraud alert generated: {alert.alert_id} - {alert.description}")
        
        return fraud_event
    
    def _calculate_rule_based_score(self, features: FraudFeatures) -> float:
        """Calculate fraud score using rule-based approach"""
        score = 0.0
        
        # High-risk indicators
        if features.new_device and features.new_location:
            score += 0.3
        elif features.new_device or features.new_location:
            score += 0.15
        
        if features.location_distance_km > self.config['location_distance_threshold_km']:
            score += 0.2
        
        if features.unusual_login_time:
            score += 0.1
        
        if features.transaction_velocity > self.config['transaction_velocity_threshold']:
            score += 0.25
        
        if features.amount_deviation_from_avg > 3:  # More than 3 standard deviations
            score += 0.2
        
        if features.failed_login_attempts_24h > 3:
            score += 0.15
        
        if features.vpn_detected or features.tor_detected or features.proxy_detected:
            score += 0.1
        
        if features.ip_reputation_score < 0.3:
            score += 0.15
        
        if features.connected_suspicious_accounts > 0:
            score += 0.1 * features.connected_suspicious_accounts
        
        if features.shared_devices > 2:
            score += 0.1
        
        if not features.mfa_enabled and (features.new_device or features.new_location):
            score += 0.1
        
        return min(score, 1.0)
    
    def _determine_risk_level(self, fraud_score: float) -> FraudRiskLevel:
        """Determine risk level based on fraud score"""
        if fraud_score >= 0.9:
            return FraudRiskLevel.CRITICAL
        elif fraud_score >= 0.7:
            return FraudRiskLevel.HIGH
        elif fraud_score >= 0.5:
            return FraudRiskLevel.MEDIUM
        elif fraud_score >= 0.3:
            return FraudRiskLevel.LOW
        else:
            return FraudRiskLevel.VERY_LOW
    
    def _identify_fraud_types(self, features: FraudFeatures, fraud_score: float) -> List[FraudType]:
        """Identify potential fraud types based on features"""
        fraud_types = []
        
        if features.new_device and features.failed_login_attempts_24h > 0:
            fraud_types.append(FraudType.ACCOUNT_TAKEOVER)
        
        if features.new_location and features.location_distance_km > 1000:
            fraud_types.append(FraudType.IDENTITY_THEFT)
        
        if features.transaction_velocity > 5 or features.amount_deviation_from_avg > 2:
            fraud_types.append(FraudType.TRANSACTION_FRAUD)
        
        if features.unusual_login_time and features.connected_suspicious_accounts > 0:
            fraud_types.append(FraudType.INSIDER_THREAT)
        
        if features.transaction_frequency_24h > 10 and features.connected_suspicious_accounts > 2:
            fraud_types.append(FraudType.MONEY_LAUNDERING)
        
        if features.vpn_detected or features.tor_detected:
            fraud_types.append(FraudType.UNAUTHORIZED_ACCESS)
        
        return fraud_types
    
    def _update_user_profile(self, fraud_event: FraudEvent):
        """Update user profile with event data"""
        user_id = fraud_event.user_id
        
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {
                'devices': set(),
                'locations': set(),
                'ip_addresses': set(),
                'fraud_score': 0.0,
                'created_at': datetime.now(),
                'last_activity': datetime.now()
            }
        
        profile = self.user_profiles[user_id]
        
        # Update profile with current event data
        if hasattr(fraud_event, 'metadata'):
            device_id = fraud_event.metadata.get('device_id')
            location = fraud_event.metadata.get('location')
            ip_address = fraud_event.metadata.get('ip_address')
            
            if device_id:
                profile['devices'].add(device_id)
            if location:
                profile['locations'].add(location)
                profile['last_location'] = location
            if ip_address:
                profile['ip_addresses'].add(ip_address)
        
        # Update fraud score (exponential moving average)
        alpha = 0.1
        profile['fraud_score'] = (alpha * fraud_event.fraud_score + 
                                 (1 - alpha) * profile.get('fraud_score', 0))
        
        profile['last_activity'] = fraud_event.timestamp
    
    def _generate_alert(self, fraud_event: FraudEvent) -> FraudAlert:
        """Generate fraud alert"""
        primary_fraud_type = fraud_event.fraud_types[0] if fraud_event.fraud_types else FraudType.TRANSACTION_FRAUD
        
        # Generate description
        description = f"Fraud detected: {primary_fraud_type.value} - Score: {fraud_event.fraud_score:.2f}"
        
        # Collect evidence
        evidence = {
            'fraud_score': fraud_event.fraud_score,
            'risk_level': fraud_event.risk_level.value,
            'fraud_types': [ft.value for ft in fraud_event.fraud_types],
            'features': {
                'new_device': fraud_event.features.new_device,
                'new_location': fraud_event.features.new_location,
                'location_distance_km': fraud_event.features.location_distance_km,
                'transaction_velocity': fraud_event.features.transaction_velocity,
                'unusual_time': fraud_event.features.unusual_login_time,
                'ip_reputation': fraud_event.features.ip_reputation_score,
                'failed_logins': fraud_event.features.failed_login_attempts_24h
            }
        }
        
        # Determine recommended actions
        recommended_actions = self.response_rules.get(fraud_event.risk_level, [ResponseAction.MONITOR])
        
        alert = FraudAlert(
            alert_id=str(uuid.uuid4()),
            event_id=fraud_event.event_id,
            user_id=fraud_event.user_id,
            fraud_type=primary_fraud_type,
            risk_level=fraud_event.risk_level,
            fraud_score=fraud_event.fraud_score,
            confidence=fraud_event.confidence,
            description=description,
            evidence=evidence,
            recommended_actions=recommended_actions,
            created_at=datetime.now()
        )
        
        return alert
    
    def execute_automated_response(self, alert: FraudAlert) -> Dict[str, Any]:
        """Execute automated response actions"""
        response_results = {
            'alert_id': alert.alert_id,
            'actions_taken': [],
            'success': True,
            'details': {}
        }
        
        for action in alert.recommended_actions:
            try:
                if action == ResponseAction.MONITOR:
                    # Increase monitoring frequency for user
                    self._increase_monitoring(alert.user_id)
                    response_results['actions_taken'].append('monitoring_increased')
                
                elif action == ResponseAction.ALERT:
                    # Send alert to security team
                    self._send_security_alert(alert)
                    response_results['actions_taken'].append('security_alert_sent')
                
                elif action == ResponseAction.CHALLENGE:
                    # Require additional authentication
                    self._require_additional_auth(alert.user_id)
                    response_results['actions_taken'].append('additional_auth_required')
                
                elif action == ResponseAction.BLOCK:
                    # Block user account temporarily
                    self._block_user_account(alert.user_id, duration_hours=24)
                    response_results['actions_taken'].append('account_blocked')
                
                elif action == ResponseAction.SUSPEND:
                    # Suspend user account
                    self._suspend_user_account(alert.user_id)
                    response_results['actions_taken'].append('account_suspended')
                
                elif action == ResponseAction.ESCALATE:
                    # Escalate to security team
                    self._escalate_to_security_team(alert)
                    response_results['actions_taken'].append('escalated_to_security')
                
                elif action == ResponseAction.INVESTIGATE:
                    # Create investigation case
                    case_id = self._create_investigation_case(alert)
                    response_results['actions_taken'].append(f'investigation_created_{case_id}')
                
            except Exception as e:
                logger.error(f"Failed to execute action {action}: {e}")
                response_results['success'] = False
                response_results['details'][action.value] = str(e)
        
        return response_results
    
    def _increase_monitoring(self, user_id: str):
        """Increase monitoring frequency for user"""
        profile = self.user_profiles.get(user_id, {})
        profile['monitoring_level'] = 'HIGH'
        profile['monitoring_until'] = datetime.now() + timedelta(hours=24)
        logger.info(f"Increased monitoring for user {user_id}")
    
    def _send_security_alert(self, alert: FraudAlert):
        """Send alert to security team"""
        # In a real implementation, this would send notifications
        logger.warning(f"SECURITY ALERT: {alert.description} - User: {alert.user_id}")
    
    def _require_additional_auth(self, user_id: str):
        """Require additional authentication for user"""
        profile = self.user_profiles.get(user_id, {})
        profile['requires_additional_auth'] = True
        profile['additional_auth_until'] = datetime.now() + timedelta(hours=24)
        logger.info(f"Additional authentication required for user {user_id}")
    
    def _block_user_account(self, user_id: str, duration_hours: int = 24):
        """Block user account temporarily"""
        profile = self.user_profiles.get(user_id, {})
        profile['account_blocked'] = True
        profile['blocked_until'] = datetime.now() + timedelta(hours=duration_hours)
        logger.warning(f"Account blocked for user {user_id} for {duration_hours} hours")
    
    def _suspend_user_account(self, user_id: str):
        """Suspend user account"""
        profile = self.user_profiles.get(user_id, {})
        profile['account_suspended'] = True
        profile['suspended_at'] = datetime.now()
        logger.critical(f"Account suspended for user {user_id}")
    
    def _escalate_to_security_team(self, alert: FraudAlert):
        """Escalate alert to security team"""
        # In a real implementation, this would create tickets, send emails, etc.
        logger.critical(f"ESCALATED TO SECURITY TEAM: {alert.description}")
    
    def _create_investigation_case(self, alert: FraudAlert) -> str:
        """Create investigation case"""
        case_id = str(uuid.uuid4())
        # In a real implementation, this would create a case in investigation system
        logger.info(f"Investigation case created: {case_id} for alert {alert.alert_id}")
        return case_id
    
    def analyze_transaction_patterns(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Analyze transaction patterns for suspicious activity"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        user_events = [
            event for event in self.events
            if event.user_id == user_id and event.timestamp >= cutoff_date
        ]
        
        if not user_events:
            return {'error': 'No events found for analysis'}
        
        analysis = {
            'user_id': user_id,
            'analysis_period_days': days,
            'total_events': len(user_events),
            'fraud_events': len([e for e in user_events if e.fraud_score > 0.5]),
            'average_fraud_score': np.mean([e.fraud_score for e in user_events]),
            'risk_distribution': {},
            'fraud_types_detected': [],
            'suspicious_patterns': [],
            'recommendations': []
        }
        
        # Risk distribution
        risk_counts = defaultdict(int)
        for event in user_events:
            risk_counts[event.risk_level.value] += 1
        analysis['risk_distribution'] = dict(risk_counts)
        
        # Fraud types
        fraud_types = set()
        for event in user_events:
            fraud_types.update([ft.value for ft in event.fraud_types])
        analysis['fraud_types_detected'] = list(fraud_types)
        
        # Detect suspicious patterns
        analysis['suspicious_patterns'] = self._detect_user_patterns(user_events)
        
        # Generate recommendations
        analysis['recommendations'] = self._generate_user_recommendations(user_events, analysis)
        
        return analysis
    
    def _detect_user_patterns(self, events: List[FraudEvent]) -> List[Dict[str, Any]]:
        """Detect suspicious patterns in user events"""
        patterns = []
        
        # Pattern 1: Rapid escalation in fraud scores
        fraud_scores = [e.fraud_score for e in events[-10:]]  # Last 10 events
        if len(fraud_scores) >= 5:
            trend = np.polyfit(range(len(fraud_scores)), fraud_scores, 1)[0]
            if trend > 0.05:  # Increasing trend
                patterns.append({
                    'type': 'escalating_fraud_scores',
                    'description': 'Fraud scores are increasing over time',
                    'severity': 'HIGH' if trend > 0.1 else 'MEDIUM'
                })
        
        # Pattern 2: Clustering of high-risk events
        high_risk_events = [e for e in events if e.risk_level in [FraudRiskLevel.HIGH, FraudRiskLevel.CRITICAL]]
        if len(high_risk_events) >= 3:
            # Check if they're clustered in time
            timestamps = [e.timestamp for e in high_risk_events]
            time_diffs = [(timestamps[i+1] - timestamps[i]).total_seconds() / 3600 for i in range(len(timestamps)-1)]
            avg_time_diff = np.mean(time_diffs)
            
            if avg_time_diff < 6:  # Less than 6 hours between high-risk events
                patterns.append({
                    'type': 'clustered_high_risk_events',
                    'description': f'{len(high_risk_events)} high-risk events in short timeframe',
                    'severity': 'CRITICAL'
                })
        
        # Pattern 3: Consistent fraud type
        fraud_type_counts = defaultdict(int)
        for event in events:
            for fraud_type in event.fraud_types:
                fraud_type_counts[fraud_type.value] += 1
        
        dominant_fraud_type = max(fraud_type_counts.items(), key=lambda x: x[1]) if fraud_type_counts else None
        if dominant_fraud_type and dominant_fraud_type[1] >= 3:
            patterns.append({
                'type': 'consistent_fraud_type',
                'description': f'Repeated {dominant_fraud_type[0]} patterns detected',
                'severity': 'MEDIUM'
            })
        
        return patterns
    
    def _generate_user_recommendations(self, events: List[FraudEvent], analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on user analysis"""
        recommendations = []
        
        avg_fraud_score = analysis['average_fraud_score']
        fraud_events_count = analysis['fraud_events']
        
        if avg_fraud_score > 0.7:
            recommendations.append("Consider immediate account review and enhanced monitoring")
        elif avg_fraud_score > 0.5:
            recommendations.append("Implement additional authentication requirements")
        
        if fraud_events_count > 5:
            recommendations.append("Conduct comprehensive security assessment")
        
        # Check for specific fraud types
        fraud_types = analysis['fraud_types_detected']
        if 'ACCOUNT_TAKEOVER' in fraud_types:
            recommendations.append("Force password reset and enable MFA")
        if 'MONEY_LAUNDERING' in fraud_types:
            recommendations.append("Review transaction patterns and report to compliance")
        if 'INSIDER_THREAT' in fraud_types:
            recommendations.append("Conduct background check and access review")
        
        # Check for suspicious patterns
        for pattern in analysis['suspicious_patterns']:
            if pattern['severity'] == 'CRITICAL':
                recommendations.append(f"Immediate action required: {pattern['description']}")
        
        if not recommendations:
            recommendations.append("Continue regular monitoring")
        
        return recommendations
    
    def get_fraud_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive fraud detection dashboard data"""
        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        
        # Recent events and alerts
        recent_events = [e for e in self.events if e.timestamp >= last_24h]
        recent_alerts = [a for a in self.alerts if a.created_at >= last_24h]
        weekly_events = [e for e in self.events if e.timestamp >= last_7d]
        
        # Risk distribution
        risk_distribution = defaultdict(int)
        for event in recent_events:
            risk_distribution[event.risk_level.value] += 1
        
        # Fraud type distribution
        fraud_type_distribution = defaultdict(int)
        for event in recent_events:
            for fraud_type in event.fraud_types:
                fraud_type_distribution[fraud_type.value] += 1
        
        # Top risky users
        user_risk_scores = {}
        for user_id, profile in self.user_profiles.items():
            user_risk_scores[user_id] = profile.get('fraud_score', 0)
        
        top_risky_users = sorted(user_risk_scores.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'timestamp': now.isoformat(),
            'events': {
                'total_events': len(self.events),
                'events_24h': len(recent_events),
                'events_7d': len(weekly_events),
                'fraud_events_24h': len([e for e in recent_events if e.fraud_score > 0.5]),
                'high_risk_events_24h': len([e for e in recent_events 
                                           if e.risk_level in [FraudRiskLevel.HIGH, FraudRiskLevel.CRITICAL]])
            },
            'alerts': {
                'total_alerts': len(self.alerts),
                'alerts_24h': len(recent_alerts),
                'unresolved_alerts': len([a for a in self.alerts if not a.resolved]),
                'critical_alerts_24h': len([a for a in recent_alerts if a.risk_level == FraudRiskLevel.CRITICAL])
            },
            'risk_distribution': dict(risk_distribution),
            'fraud_type_distribution': dict(fraud_type_distribution),
            'top_risky_users': top_risky_users,
            'models': {
                'fraud_classifier_trained': hasattr(self.fraud_classifier, 'predict'),
                'anomaly_detector_trained': hasattr(self.anomaly_detector, 'predict'),
                'total_profiles': len(self.user_profiles)
            },
            'transaction_graph': {
                'total_nodes': len(self.transaction_graph.user_nodes),
                'total_edges': len(self.transaction_graph.transaction_edges),
                'suspicious_patterns': len(self.transaction_graph.detect_suspicious_patterns())
            }
        }

# Example usage and testing
if __name__ == "__main__":
    # Initialize fraud detection engine
    fraud_engine = FraudDetectionEngine()
    
    # Create sample event data
    sample_event = {
        'user_id': 'user_123',
        'event_type': 'transaction',
        'timestamp': datetime.now(),
        'device_id': 'new_device_456',
        'location': 'Tokyo, Japan',
        'ip_address': '203.0.113.1',
        'transaction_amount': 50000,
        'session_duration': 300,
        'vpn_detected': True
    }
    
    # Detect fraud
    fraud_event = fraud_engine.detect_fraud(sample_event)
    
    print(f"Fraud Detection Results:")
    print(f"Event ID: {fraud_event.event_id}")
    print(f"Fraud Score: {fraud_event.fraud_score:.3f}")
    print(f"Risk Level: {fraud_event.risk_level.value}")
    print(f"Fraud Types: {[ft.value for ft in fraud_event.fraud_types]}")
    print(f"Confidence: {fraud_event.confidence:.3f}")
    
    # Get dashboard data
    dashboard = fraud_engine.get_fraud_dashboard()
    print(f"\nFraud Dashboard Summary:")
    print(f"Total Events: {dashboard['events']['total_events']}")
    print(f"Events (24h): {dashboard['events']['events_24h']}")
    print(f"Fraud Events (24h): {dashboard['events']['fraud_events_24h']}")
    print(f"Total Alerts: {dashboard['alerts']['total_alerts']}")
    print(f"Unresolved Alerts: {dashboard['alerts']['unresolved_alerts']}")